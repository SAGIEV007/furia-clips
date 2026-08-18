"""Turn the Campaign Hub entity table into a name lexicon Furia can use offline.

The Hub has extracted 52.282 entity mentions across 12.998 distinct spellings
from real transcripts of this speaker. That is two orders of magnitude more
coverage than the 27 names written by hand, and it comes with a role for each
one — ally, villain, institution, place — which the headline generator needs
just as much as the caption corrector needs the spelling.

There is one trap in it, and it decides the whole design. **Frequency is not
authority.** The Hub extracted those names from automatic captions, so it
inherited their mistakes: "Nicolas Ferreira" appears 47 times and "Nikolas
Ferreira" 12, and the rare spelling is the correct one — that is the deputy's
actual name. A script that crowned the most frequent form would teach Furia to
misspell him confidently, which is worse than not knowing him at all.

So the Hub is used for what it really knows and no further:

* **which spellings are the same person** — clustered phonetically, since a
  caption that heard "Vorkaro" and one that heard "Vorcaro" are one entity;
* **the role that entity plays** in this speaker's material.

The canonical spelling comes from somewhere else. A hand-curated name is
canonical and is marked confirmed. Everything else is written out as a cluster
awaiting review, with the most frequent form only as a *suggestion*. Nothing
unconfirmed ever rewrites a caption — it is offered to the editor, who decides.

Run:  python scripts/lexico_do_chub.py <export.txt>
where each line is  nome|ocorrencias|papel
"""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.caption_lexicon import phonetic_key  # noqa: E402


REPO = Path(__file__).resolve().parent.parent
CURATED = REPO / "data" / "lexico" / "nomes_missao.json"
OUTPUT = REPO / "data" / "lexico" / "entidades_chub.json"

# Two spellings belong to the same entity when their phonetic keys are this
# close. Measured against the real clusters in the export: "vorcaro/vorkaro"
# needs 1, "vorcaro/forcaro" needs 1, "bukele/bukel" needs 1. Going to 3 started
# merging distinct surnames, so this is the ceiling, not a tuning knob.
MAX_KEY_DISTANCE = 2
# A single letter of slack is meaningless on a short word: "Kim" and "Kin" are
# one edit apart and so are "Lula" and "Lulu". Below this length demand an
# exact phonetic match.
SHORT_NAME_CHARS = 6


def _distance(left: str, right: str) -> int:
    """Levenshtein, small inputs, no dependency."""
    if left == right:
        return 0
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, start=1):
        current = [i]
        for j, b in enumerate(right, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def _same_entity(left: dict, right: dict) -> bool:
    """Whether two spellings are one name heard two ways.

    The distance is measured word by word, not over the joined key. Compared as
    one string, "Joesley Batista" and "Wesley Batista" sit inside the budget
    because the shared surname pays for the different first name — and they are
    two people, brothers, both of whom this speaker names. Per word the first
    names are two edits apart and the merge does not happen.
    """
    if len(left["words"]) != len(right["words"]):
        return False
    total = 0
    for a, b in zip(left["key"].split(), right["key"].split()):
        budget = 0 if min(len(a), len(b)) <= SHORT_NAME_CHARS else 1
        step = _distance(a, b)
        if step > budget:
            return False
        total += step
    return total <= MAX_KEY_DISTANCE


def _curated_names() -> dict[str, str]:
    """Spellings a person vouched for, keyed phonetically."""
    try:
        payload = json.loads(CURATED.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    confirmed = {}
    for entry in payload.get("nomes") or []:
        canonical = str(entry.get("canonico") or "").strip()
        if not canonical:
            continue
        for spelling in [canonical, *(entry.get("variantes") or [])]:
            key = " ".join(phonetic_key(word) for word in str(spelling).split())
            confirmed[key] = canonical
    return confirmed


def build(export_path: Path) -> dict:
    rows = []
    for line in export_path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split("|")
        if len(parts) != 3 or not parts[0]:
            continue
        name, count, role = parts[0].strip(), parts[1].strip(), parts[2].strip()
        words = name.split()
        rows.append({
            "name": name,
            "count": int(count) if count.isdigit() else 0,
            "role": role,
            "words": words,
            "key": " ".join(phonetic_key(word) for word in words),
        })
    rows.sort(key=lambda row: (-row["count"], row["name"]))

    clusters: list[list[dict]] = []
    for row in rows:
        for cluster in clusters:
            if _same_entity(cluster[0], row):
                cluster.append(row)
                break
        else:
            clusters.append([row])

    curated = _curated_names()
    entries = []
    for cluster in clusters:
        spellings = sorted(cluster, key=lambda row: -row["count"])
        confirmed_name = next((curated[row["key"]] for row in spellings if row["key"] in curated), None)
        head = spellings[0]
        variants = [row["name"] for row in spellings if row["name"] != (confirmed_name or head["name"])]
        # Curated names with no new spelling to add are still written out: the
        # role is the other half of what the Hub knows, and dropping the entry
        # dropped "Kim Kataguiri: ally" and "Comando Vermelho: villain" from the
        # table the headline generator reads.
        entries.append({
            "canonico": confirmed_name or head["name"],
            "confirmado": confirmed_name is not None,
            "variantes": variants,
            "papel": head["role"],
            "mencoes_chub": sum(row["count"] for row in spellings),
        })

    entries.sort(key=lambda entry: (-entry["mencoes_chub"], entry["canonico"]))
    pending = [entry for entry in entries if not entry["confirmado"] and entry["variantes"]]
    return {
        "schema_version": "furia-lexico-chub-v1",
        "origem": "Campaign Hub, tabela entities (52.282 menções, 12.998 grafias distintas)",
        "nota": (
            "Agrupamento e papel vêm do Campaign Hub. A grafia canônica NÃO vem: "
            "o Hub extraiu esses nomes de legendas automáticas e herdou os erros delas "
            "— 'Nicolas Ferreira' aparece mais vezes que 'Nikolas Ferreira', e a forma "
            "rara é a certa. Só entradas com confirmado=true reescrevem legenda. As "
            "demais ficam como sugestão para o editor aprovar."
        ),
        "contrato": "confirmado=false nunca corrige em silêncio; no máximo sinaliza.",
        "total": len(entries),
        "confirmados": sum(1 for entry in entries if entry["confirmado"]),
        "aguardando_revisao": len(pending),
        "entradas": entries,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    payload = build(Path(sys.argv[1]))
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{OUTPUT}: {payload['total']} entradas, {payload['confirmados']} confirmadas, "
          f"{payload['aguardando_revisao']} aguardando revisão do editor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

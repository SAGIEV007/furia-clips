#!/usr/bin/env python3
"""A prova de que ele trabalhou — e não só de que ele disse que trabalhou.

POR QUE ISTO EXISTE
-------------------
O editor perguntou a coisa certa:

    "como vou saber se todas as skills estão sendo usadas, agentes, etc?"

Perguntar ao agente não serve. Um agente responde "sim, segui todas as
instruções" com a mesma facilidade tendo seguido ou não — e um modelo pequeno
responde isso com mais facilidade ainda. É o mesmo problema que a régua já
resolve para o corte: um número que a máquina dá sobre si mesma não mede nada.

Então este relatório não pergunta nada a ninguém. Ele lê os RASTROS, que são
coisas que só existem se o trabalho aconteceu de verdade:

    o histórico de medições   — só enche quando a régua roda
    os commits                — só existem quando código mudou
    a data do ESTADO.md       — só muda quando alguém escreve nele
    a branch                  — diz se ele mexeu onde não devia

E termina com a única verificação que fecha o circuito: um número que o editor
pode conferir com as próprias mãos, na própria máquina.

O QUE ELE NÃO CONSEGUE PROVAR
-----------------------------
Quantos bots rodaram, e qual modelo estava em cada um. Isso é de dentro do
Hermes; o repositório não vê. E, no desenho, não precisa ver: quem decide se uma
mudança fica é o número da régua, não o modelo que a propôs. Um bot preguiçoso
aparece aqui como experimento que não mediu, não como bot preguiçoso.

USO
---
    python scripts/prova.py            # últimas 24 horas
    python scripts/prova.py --horas 8  # desde que você foi dormir
"""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
HISTORICO = RAIZ / "docs" / "hermes" / "medicoes.txt"
ESTADO = RAIZ / "docs" / "hermes" / "ESTADO.md"
CARTA = RAIZ / "docs" / "hermes" / "CARTA.md"
SKILLS = RAIZ / "docs" / "hermes" / "skills"

BRANCH_DO_TREINO = "furia-treino-noturno"
BRANCH_DO_EDITOR = "claude/repo-access-commits-imgjmk"

# As instruções que qualquer modelo deveria ter lido antes de agir. A presença
# não prova a leitura — nada prova a leitura. A ausência, porém, prova que não
# leu, e isso já é metade da pergunta respondida.
INSTRUCOES = [
    (CARTA, "as ordens permanentes"),
    (ESTADO, "o quadro de aviso"),
    (SKILLS / "modo-autonomo.md", "o ciclo de trabalho sozinho"),
    (SKILLS / "medir-o-corte.md", "como saber se melhorou"),
    (SKILLS / "nota-de-passagem.md", "como continuar quando o modelo troca"),
    (SKILLS / "caderno-de-vereditos.md", "como anotar o seu julgamento"),
]


def _git(*args, padrao=""):
    try:
        return subprocess.run(
            ["git", *args], cwd=RAIZ, capture_output=True, text=True, timeout=20, check=False
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return padrao


def ler_medicoes(desde: datetime) -> list[dict]:
    if not HISTORICO.is_file():
        return []
    linhas = []
    for linha in HISTORICO.read_text(encoding="utf-8", errors="replace").splitlines():
        partes = [p.strip() for p in linha.split("|")]
        if len(partes) < 3:
            continue
        try:
            quando = datetime.fromisoformat(partes[0])
        except ValueError:
            continue
        if quando < desde:
            continue
        linhas.append({"quando": quando, "rotulo": partes[1], "resto": partes[2:]})
    return linhas


def parear(medicoes: list[dict]) -> tuple[list, list]:
    """Um experimento honesto tem duas medições: antes e depois, mesmo nome.

    Medir só o antes é a assinatura de quem mudou o código e não conferiu.
    Medir só o depois é pior: sem o antes não há como saber se subiu.
    """
    antes, depois = {}, {}
    for m in medicoes:
        rotulo = m["rotulo"]
        if rotulo.startswith("antes-"):
            antes[rotulo[6:]] = m
        elif rotulo.startswith("depois-"):
            depois[rotulo[7:]] = m
    completos = [(nome, antes[nome], depois[nome]) for nome in antes if nome in depois]
    pela_metade = (
        [(nome, "mediu antes e não voltou para medir depois") for nome in antes if nome not in depois]
        + [(nome, "mediu depois sem ter medido antes") for nome in depois if nome not in antes]
    )
    return completos, sorted(pela_metade)


def _blocos(medicao) -> str:
    for campo in medicao["resto"]:
        if campo.startswith("blocos "):
            return campo[7:]
    return "?"


def main():
    parser = argparse.ArgumentParser(description="Mostra o rastro do trabalho autônomo.")
    parser.add_argument("--horas", type=int, default=24, help="janela a olhar (padrão 24)")
    args = parser.parse_args()

    desde = datetime.now() - timedelta(hours=args.horas)  # noqa: DTZ005 — hora do relógio dele
    branch = _git("branch", "--show-current")
    medicoes = ler_medicoes(desde)
    completos, pela_metade = parear(medicoes)
    commits = [c for c in _git("log", f"--since={args.horas}.hours", "--oneline").splitlines() if c]
    tocou_sua_branch = _git(
        "log", f"--since={args.horas}.hours", "--oneline", BRANCH_DO_EDITOR
    ).splitlines()

    def ok(condicao):
        return "ok" if condicao else "OLHE ISTO"

    print(f"\n  PRESTAÇÃO DE CONTAS — últimas {args.horas} horas\n")

    print("  Onde ele mexeu")
    print(f"    branch de trabalho ............ {branch or '?':<28} {ok(branch == BRANCH_DO_TREINO)}")
    print(f"    mexeu na SUA branch? .......... {'sim, ' + str(len(tocou_sua_branch)) + ' commit(s)' if tocou_sua_branch else 'não':<28} {ok(not tocou_sua_branch)}")
    if tocou_sua_branch:
        print("    (trabalho sozinho nunca devia tocar aí. Se foi você acompanhando,")
        print("     está certo — a linha só acusa o que aconteceu sem você olhando.)")
    print()

    print("  O que ele mediu")
    print(f"    medições registradas .......... {len(medicoes)}")
    print(f"    experimentos completos ........ {len(completos):<28} {ok(completos or not medicoes)}")
    print(f"    experimentos pela metade ...... {len(pela_metade):<28} {ok(not pela_metade)}")
    for nome, motivo in pela_metade:
        print(f"        '{nome}': {motivo}")
    print()

    if completos:
        print("  Cada experimento, antes e depois")
        for nome, a, d in completos:
            de, para = _blocos(a), _blocos(d)
            seta = "->" if de != para else "=="
            print(f"    {nome:<26} blocos {de} {seta} {para}")
        print()
    elif medicoes:
        print("  Ele mediu, mas nenhum experimento fechou o par antes/depois.")
        print("  Sem o par não dá para saber se alguma mudança melhorou alguma coisa.\n")

    print("  O que ele mudou")
    print(f"    commits no período ............ {len(commits)}")
    if commits:
        for c in commits[:8]:
            print(f"        {c[:88]}")
        if len(commits) > 8:
            print(f"        ... e mais {len(commits) - 8}")
    if commits and not completos:
        print("    ATENÇÃO: mudou código sem nenhum experimento medido de ponta a ponta.")
    print()

    print("  O quadro de aviso")
    if ESTADO.is_file():
        idade = datetime.now() - datetime.fromtimestamp(ESTADO.stat().st_mtime)  # noqa: DTZ005, DTZ006
        horas = idade.total_seconds() / 3600
        quando = f"há {horas:.0f} h" if horas >= 1 else f"há {idade.total_seconds() / 60:.0f} min"
        atual = horas <= args.horas
        print(f"    ESTADO.md escrito ............. {quando:<28} {ok(atual)}")
        if commits and not atual:
            print("    Ele mudou código e não escreveu no quadro. A próxima sessão")
            print("    vai começar sem saber o que esta fez.")
    else:
        print("    ESTADO.md ..................... SUMIU                        OLHE ISTO")
    print()

    print("  As instruções que ele deveria ter lido")
    faltando = [nome for caminho, nome in INSTRUCOES if not caminho.is_file()]
    for caminho, nome in INSTRUCOES:
        print(f"    {nome:<30} {'presente' if caminho.is_file() else 'FALTANDO':<28}"
              f"{'' if caminho.is_file() else 'OLHE ISTO'}")
    if faltando:
        print("    Um arquivo que não está aqui não foi lido por ninguém.")
    print()

    print("  ─────────────────────────────────────────────────────────────────")
    print("  CONFIRA VOCÊ MESMO — é isto que fecha o circuito")
    print()
    if completos:
        ultimo = max(completos, key=lambda item: item[2]["quando"])
        print(f"    Ele diz que o último experimento ('{ultimo[0]}') terminou em")
        print(f"    blocos {_blocos(ultimo[2])}.")
    elif medicoes:
        print(f"    A última medição que ele registrou foi blocos {_blocos(medicoes[-1])}.")
    else:
        print("    Ele não registrou medição nenhuma no período.")
    print()
    print("    Rode você mesmo, nesta máquina:")
    print()
    print("        python scripts/regua.py")
    print()
    print("    Se der um número diferente, o que ele te contou não bate com o")
    print("    programa que está aqui. Este é o único teste que ele não tem como")
    print("    responder por você.")
    print()

    print("  O que este relatório NÃO vê")
    print("    Quantos bots rodaram e qual modelo estava em cada um. Isso é de")
    print("    dentro do Hermes. Não faz falta: quem decide se uma mudança fica é")
    print("    o número da régua, não o modelo que a propôs. Bot que não trabalhou")
    print("    aparece aqui como experimento que não mediu.")
    print()


if __name__ == "__main__":
    main()

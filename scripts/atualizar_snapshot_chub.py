"""Reconstroi o snapshot local do Chub que o app le na inicializacao.

Uso:
    python scripts/atualizar_snapshot_chub.py

O app le `FuriaClipsData/campaign_hub/profile.json` ao subir. Se esse arquivo
estiver invalido ou vazio, o Furia trabalha as cegas -- sem os blocos do acervo
que dizem onde cada argumento comeca e termina.

ARMADILHAS ja encontradas (01/09/2026), documentadas para nao se repetirem:

1. `audience_priors` como dicionario invalida o arquivo INTEIRO em silencio.
   O validador exige lista; um dict faz `normalize_snapshot` devolver None e o
   app registra apenas "Chub snapshot indisponivel: invalid".

2. Os blocos precisam usar `startS`/`endS` (camelCase), nao `start_s`/`end_s`.
   Com o nome errado cada bloco e descartado individualmente e o arquivo passa
   de "invalid" para "empty" -- parece melhor, continua inutil.

Este script grava no formato correto e VERIFICA o resultado antes de terminar.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PERFIL = os.path.join(
    os.path.expanduser("~"), "FuriaClipsData", "campaign_hub", "profile.json"
)


def para_formato_do_app(bloco):
    """Converte um bloco do banco do Chub para o formato que o app aceita."""
    return {
        "videoId": bloco["external_id"],
        "startS": float(bloco["start_s"]),
        "endS": float(bloco["end_s"]),
        "title": bloco["title"],
        "summary": bloco["summary"],
        "triggerQuestion": bloco["trigger_question"],
        "category": bloco["category"],
        "topics": bloco["topics"] or [],
        "renanSpeaking": bloco["renan_speaking"],
        "needsContext": bloco["needs_context"],
        "densityRank": int(bloco["density_rank"] or 0),
        "selfContainedRank": int(bloco["self_contained_rank"] or 0),
        "riskFlags": bloco["risk_flags"] or [],
        "trust_tier": "qa_gated",
    }


def gravar(blocos_do_chub, conta="@renansantosmbl"):
    perfil = {"default_account": conta, "accounts": {}, "meta": {}}
    if os.path.exists(PERFIL):
        perfil = json.load(io.open(PERFIL, encoding="utf-8"))

    dados = perfil.setdefault("accounts", {}).setdefault(conta, {})
    dados["acervo_blocks"] = [para_formato_do_app(b) for b in blocos_do_chub]
    dados.setdefault("hook_observations", [])
    dados.setdefault("acervo_pauta", [])
    # Lista, nunca dict — ver armadilha 1 no topo.
    dados["audience_priors"] = []
    dados.setdefault("performance", {"metric": "ratio", "rows": []})

    os.makedirs(os.path.dirname(PERFIL), exist_ok=True)
    io.open(PERFIL, "w", encoding="utf-8").write(
        json.dumps(perfil, ensure_ascii=False, indent=1)
    )
    return len(dados["acervo_blocks"])


def verificar():
    """Confirma no proprio validador do app, nao no otimismo."""
    from modules.campaign_hub import snapshot_status

    status = snapshot_status(PERFIL)
    print(f"status ............ {status.get('status')}")
    print(f"disponivel ........ {status.get('available')}")
    print(f"blocos ............ {status.get('total_acervo_blocks')}")
    print(f"influencia ranking  {status.get('influences_ranking')}")
    return bool(status.get("available")) and int(status.get("total_acervo_blocks") or 0) > 0


if __name__ == "__main__":
    print("Este script precisa dos blocos vindos do MCP do Chub.")
    print("Execute a consulta com chub_sql e passe as linhas para gravar().")
    print()
    print("Estado atual do snapshot:")
    ok = verificar()
    sys.exit(0 if ok else 1)

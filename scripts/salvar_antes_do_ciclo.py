#!/usr/bin/env python3
"""Salva trabalho nao commitado ANTES de qualquer ciclo automatico.

MOTIVO (incidente 2026-09-01, 21:05): o cron `furia-autonomous-cycle` executou
`git reset` e apagou edicoes em andamento -- o modulo `fronteira_assunto.py`, os
testes e a integracao no `clip_selector.py` sumiram no meio da sessao.

O prompt do cron JA PROIBIA isso em texto ("NUNCA 'corrija' revertendo
arquivos", com as palavras reset/stash/checkout/clean citadas). A proibicao foi
desobedecida mesmo assim.

LICAO: instrucao em linguagem natural nao e garantia. Trabalho so esta seguro
quando existe um COMMIT. Este script cria esse commit automaticamente, num
branch de seguranca, antes de qualquer ciclo comecar.

Uso (primeira linha do ciclo automatico):
    python scripts/salvar_antes_do_ciclo.py

Nao interrompe nada: se nao houver o que salvar, sai em silencio com codigo 0.
"""
import subprocess
import sys
from datetime import datetime

REPO = r"C:/Users/70156213125/furia-clips"


def git(*args, check=True):
    r = subprocess.run(
        ["git", "-C", REPO, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} falhou: {r.stderr.strip()}")
    return r.stdout.strip()


def main():
    sujo = git("status", "--porcelain")
    if not sujo:
        print("[salvaguarda] nada pendente, nada a salvar")
        return 0

    n = len([l for l in sujo.splitlines() if l.strip()])
    carimbo = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_atual = git("rev-parse", "--abbrev-ref", "HEAD")
    tag = f"salvaguarda/{carimbo}"

    print(f"[salvaguarda] {n} arquivo(s) pendente(s) em {branch_atual}")

    # Commit de seguranca no branch atual, sem trocar de contexto: o proximo
    # passo do ciclo continua exatamente onde estava, mas agora com rede.
    git("add", "-A")
    msg = (
        f"wip: salvaguarda automatica {carimbo}\n\n"
        f"Commit criado por scripts/salvar_antes_do_ciclo.py antes de um ciclo\n"
        f"automatico, para que nenhum `git reset` do ciclo apague trabalho em\n"
        f"andamento. Incidente que originou esta trava: 2026-09-01 21:05.\n\n"
        f"Arquivos afetados:\n{sujo}\n"
    )
    git("commit", "-q", "-m", msg)
    novo = git("rev-parse", "--short", "HEAD")

    # Marca com tag para achar depois mesmo se o branch andar.
    try:
        git("tag", tag)
        print(f"[salvaguarda] commit {novo} criado e marcado como {tag}")
    except RuntimeError:
        print(f"[salvaguarda] commit {novo} criado (tag falhou, sem problema)")

    print(f"[salvaguarda] para inspecionar:  git -C {REPO} show {novo}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        # Nunca derrubar o ciclo por causa da salvaguarda.
        print(f"[salvaguarda] erro nao fatal: {exc}")
        sys.exit(0)

"""O que o programa aprendeu com o editor.

O PROBLEMA, NAS PALAVRAS DELE
-----------------------------
    "quando eu mandar links de lives recentes, essas lives não vão estar no
     chub, então precisam ter aprendido padrões de cortes anteriores para
     funcionarem corretamente"

Ele está certo, e o diagnóstico dele é preciso. Hoje o motor tem duas fontes de
número, e nenhuma das duas serve para uma live de ontem:

    o espelho do CHUB   mede 5.339 cortes JÁ PUBLICADOS — três pesos, e só
    os blocos do Acervo  são a régua, mas só existem para vídeo catalogado

Numa live recente não há bloco do Acervo, e o motor cai nas regras fixas — que
são palpites meus com cara de ciência. É exatamente onde ele mais precisa de
ajuda e onde tem menos.

O QUE ESTE ARQUIVO FAZ
----------------------
Transforma o julgamento dele em número, e o número entra no motor pela mesma
porta por onde entram os pesos do CHUB (`espelho_chub.portoes`). Duas fontes:

    o caderno de vereditos    "3 ok", "4 ok mas final cortado"
    os cortes que ele fez     começo e fim que ELE escolheu, no vídeo dele

A segunda é a mais valiosa e é a que resolve o problema da live recente: um
corte que ele fez à mão é um gabarito que não depende do CHUB. Ele é a resposta
certa, para aquele vídeo, escrita por quem decide.

O QUE ISTO NÃO É
----------------
Não é rede neural, não é "treinar um modelo". É calibração medida, e a
diferença importa: cada número daqui tem uma conta de uma linha que dá para
conferir na mão, e um motivo em português na tela. Um sistema que ele não possa
auditar seria pior que os palpites, porque erraria sem deixar rastro.

A REGRA QUE NÃO SE QUEBRA (NORTE §15)
-------------------------------------
Só entra aqui o que veio de fora do programa: o veredito dele e o corte dele.
Nada que o Furia disse sobre o próprio trabalho vira peso. Um motor que aprende
com a própria opinião só aprende a concordar consigo mesmo.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

# Quantos casos são precisos antes de um número do editor mexer no motor.
# Abaixo disto, uma etiqueta a mais vira uma mudança de rumo, e o motor passa a
# perseguir o último clipe que ele reprovou em vez do padrão dele.
MINIMO_DE_CASOS = 8

# Teto do ajuste, em POR CENTO do peso atual — não em pontos de nota. Trinta
# por cento move o número o bastante para a régua enxergar e pouco o bastante
# para um sinal só não decidir sozinho o que é corte e o que não é.
TETO = 30.0

# A ponte entre o que ele escreve no WhatsApp e o número que o motor usa.
# Cada linha é: etiqueta do editor -> (peso do motor, sinal que o motor grava).
#
# A segunda coluna é o que permite achar o ERRO DE CALIBRAÇÃO. Se ele marcou
# "final cortado" num corte em que o motor tinha gravado `payoff_complete:
# True`, o motor não errou o peso — errou o diagnóstico. Isso é mais grave, e
# aparece separado.
O_QUE_CADA_ETIQUETA_CORRIGE: dict[str, tuple[str, str]] = {
    "fim": ("termina_sem_fechar", "payoff_complete"),
    "abertura": ("comeca_no_meio_da_frase", "starts_mid_sentence"),
    "locutor": ("abre_sem_afirmar", "opens_without_a_claim"),
    "contexto": ("contexto_incompleto", "context_complete"),
    "repetido": ("repeticao", "overlap_suspected"),
}

# Quando o sinal do motor está LIGADO, ele já acusou o defeito. Para
# `payoff_complete` e `context_complete` é o contrário: ligado quer dizer "está
# tudo bem". Estas duas leem ao contrário na hora de contar acerto e erro.
SINAL_LIGADO_E_BOM = {"payoff_complete", "context_complete"}


def _pasta(nome: str, data_dir=None) -> Path:
    raiz = Path(
        data_dir or os.environ.get("FURIA_CLIPS_DATA_DIR") or (Path.home() / "FuriaClipsData")
    )
    return raiz / nome


def ler_vereditos(data_dir=None) -> list[dict]:
    """O caderno inteiro, o último veredito de cada corte.

    O caderno só acrescenta linha — ele nunca reescreve — então um corte pode
    ter mais de um veredito quando o editor muda de ideia. A última vale, e as
    anteriores continuam no arquivo porque apagar histórico de julgamento é
    apagar o motivo de tudo isto existir.
    """
    pasta = _pasta("vereditos", data_dir)
    if not pasta.is_dir():
        return []
    por_corte: dict[tuple[str, str], dict] = {}
    for arquivo in sorted(pasta.glob("*.txt")):
        for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
            partes = [p.strip() for p in linha.split("|")]
            if len(partes) < 4 or not partes[3]:
                continue
            rodada, numero = partes[1], partes[2].lstrip("#")
            por_corte[(rodada, numero)] = {
                "rodada": rodada,
                "numero": numero,
                "veredito": partes[3].replace("-", " ").strip().lower(),
                "etiqueta": (partes[4] if len(partes) > 4 else "").strip().lower(),
                "motivo": partes[5] if len(partes) > 5 else "",
            }
    return list(por_corte.values())


def ler_manifestos(data_dir=None) -> dict[tuple[str, str], dict]:
    """O que foi enviado em cada rodada, com os sinais que o motor tinha gravado.

    Sem isto o caderno é uma lista de reclamações sem endereço: dá para saber
    que ele reprovou seis cortes por "final cortado", mas não se o motor tinha
    achado aqueles seis fechados. É a diferença entre "aperte este parafuso" e
    "o parafuso está solto em algum lugar da máquina".
    """
    pasta = _pasta("vereditos", data_dir)
    if not pasta.is_dir():
        return {}
    enviados: dict[tuple[str, str], dict] = {}
    for arquivo in sorted(pasta.glob("*.manifesto.json")):
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rodada = str(dados.get("rodada") or arquivo.stem.split(".")[0])
        for corte in dados.get("cortes") or []:
            numero = str(corte.get("numero") or "").lstrip("#")
            if numero:
                enviados[(rodada, numero)] = corte
    return enviados


def ler_cortes_do_editor(data_dir=None) -> list[dict]:
    """Os cortes que ELE fez à mão. O gabarito que não depende do CHUB.

    Formato, uma linha por corte:

        2026-09-05 14:02 | dQw4w9WgXcQ | 754.0 | 812.5 | a headline que ele usou

    É pouca coisa de escrever e é a coisa mais valiosa do sistema inteiro: diz
    onde um assunto começa e termina numa live que o Acervo nunca viu.
    """
    pasta = _pasta("cortes_do_editor", data_dir)
    if not pasta.is_dir():
        return []
    cortes = []
    for arquivo in sorted(pasta.glob("*.txt")):
        for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
            partes = [p.strip() for p in linha.split("|")]
            if len(partes) < 4:
                continue
            try:
                inicio, fim = float(partes[2]), float(partes[3])
            except ValueError:
                continue
            if fim <= inicio:
                continue
            cortes.append({
                "quando": partes[0],
                "video": partes[1],
                "start": inicio,
                "end": fim,
                "headline": partes[4] if len(partes) > 4 else "",
            })
    return cortes


def _acertos_e_erros(vereditos: list[dict], enviados: dict) -> dict[str, dict]:
    """Onde o motor acusou defeito que não havia, e onde não viu o que havia.

    Duas contas por sinal, e elas puxam para lados opostos:

        alarme falso  o motor marcou o defeito e o editor aprovou assim mesmo
        cegueira      o motor não marcou nada e o editor achou o defeito

    Cegueira faz o peso subir; alarme falso faz descer. Um sinal com muito dos
    dois não está mal calibrado — está medindo a coisa errada, e nenhum peso
    conserta isso. Por isso os dois números aparecem separados no relatório.
    """
    contas: dict[str, dict] = defaultdict(
        lambda: {"cegueira": 0, "alarme_falso": 0, "casos": 0}
    )
    for veredito in vereditos:
        corte = enviados.get((veredito["rodada"], veredito["numero"]))
        if not corte:
            continue
        sinais = corte.get("sinais") or {}
        aprovado = veredito["veredito"] == "ok"
        etiqueta = veredito["etiqueta"]

        for nome_etiqueta, (peso, sinal) in O_QUE_CADA_ETIQUETA_CORRIGE.items():
            if sinal not in sinais:
                continue
            bruto = bool(sinais.get(sinal))
            motor_acusou = (not bruto) if sinal in SINAL_LIGADO_E_BOM else bruto
            conta = contas[peso]
            conta["casos"] += 1
            if etiqueta == nome_etiqueta and not motor_acusou:
                conta["cegueira"] += 1
            elif aprovado and motor_acusou:
                conta["alarme_falso"] += 1
    return dict(contas)


def ajustes(data_dir=None) -> dict[str, float]:
    """Quanto cada peso do motor deve mudar, segundo o julgamento do editor.

    A conta é de uma linha, de propósito:

        ajuste = (cegueira - alarme_falso) / casos  ->  fração do peso atual

    Um sinal em que ele achou seis defeitos que o motor não viu, e nenhum
    exagero, ganha peso. Um sinal que o motor acusa e ele aprova assim mesmo
    perde. Abaixo de `MINIMO_DE_CASOS`, nada se mexe — e nada se mexe em
    silêncio: `explicar()` diz por quê.
    """
    contas = _acertos_e_erros(ler_vereditos(data_dir), ler_manifestos(data_dir))
    resultado: dict[str, float] = {}
    for peso, conta in contas.items():
        if conta["casos"] < MINIMO_DE_CASOS:
            continue
        fracao = (conta["cegueira"] - conta["alarme_falso"]) / conta["casos"]
        if abs(fracao) < 0.05:
            continue
        resultado[peso] = max(-TETO, min(TETO, round(fracao * 100, 1)))
    return resultado


def explicar(data_dir=None) -> list[dict]:
    """O mesmo cálculo, com o motivo por extenso — para a tela e para o Hermes."""
    contas = _acertos_e_erros(ler_vereditos(data_dir), ler_manifestos(data_dir))
    linhas = []
    for peso, conta in sorted(contas.items()):
        casos = conta["casos"]
        if casos < MINIMO_DE_CASOS:
            motivo = f"só {casos} caso(s); preciso de {MINIMO_DE_CASOS} para mexer"
            ajuste = 0.0
        else:
            fracao = (conta["cegueira"] - conta["alarme_falso"]) / casos
            ajuste = max(-TETO, min(TETO, round(fracao * 100, 1)))
            if abs(fracao) < 0.05:
                motivo = "o motor e o editor concordam; nada a corrigir"
                ajuste = 0.0
            elif ajuste > 0:
                motivo = (
                    f"{conta['cegueira']} vez(es) ele viu o defeito e o motor não; "
                    f"o desconto sobe"
                )
            else:
                motivo = (
                    f"{conta['alarme_falso']} vez(es) o motor acusou e ele aprovou "
                    f"assim mesmo; o desconto desce"
                )
        linhas.append({
            "peso": peso, "ajuste": ajuste, "casos": casos,
            "cegueira": conta["cegueira"], "alarme_falso": conta["alarme_falso"],
            "motivo": motivo,
        })
    return linhas


def gabarito_do_editor(video: str, data_dir=None) -> list[dict[str, Any]]:
    """Os cortes dele num vídeo, no formato de bloco que a régua já lê.

    É isto que faz a régua funcionar numa live de ontem. O Acervo não tem
    aquele vídeo; ele tem — porque cortou. Cada corte dele vira um bloco de
    referência com um corte esperado, e todo o resto do sistema continua igual.
    """
    cortes = [c for c in ler_cortes_do_editor(data_dir) if c["video"] == video]
    return [
        {
            "start": round(corte["start"], 2),
            "end": round(corte["end"], 2),
            "dur": round(corte["end"] - corte["start"], 2),
            "cortes": 1,
            "titulo": corte["headline"],
            "q": "",
            "fonte_do_gabarito": "editor",
        }
        for corte in sorted(cortes, key=lambda c: c["start"])
    ]

"""Recuo do inicio do corte ate a fronteira do assunto.

MOTIVO (medido 2026-09-01, scripts/bench_contexto.py contra 63 blocos do
Garimpo): 0% dos cortes abriam na fronteira do assunto. O seletor escolhia o
pico de energia da fala e comecava ali -- no meio da resposta, sem a pergunta
que a originou.

As tres pesquisas de 01/09 convergiram na MESMA acao numero 1:

  - fronteira-topico-2026-09-01.md: o defeito tem nome na literatura,
    'contextual smearing' por 'detection lag'. A correcao e recuar ate o inicio
    da unidade de fala anterior, nunca cortar no ponto de disparo.
  - autossuficiencia-trecho-2026-09-01.md: demonstrativo orfao nos primeiros
    tokens e sinal barato e limpo de dependencia.
  - gancho-abertura-retencao-2026-09-01.md: rejeitar abertura protocolar e
    deslocar o inicio para a primeira sentenca com carga.

DADO QUE SUSTENTA (criterio-autossuficiencia-chub-2026-09-01.md, 18.075 trechos
julgados): 100% dos trechos do acervo tem `trigger_question` preenchida, e
justificativas de trecho nota>=90 citam a pergunta 3,3x mais que as de nota<=30.

VALIDACAO CONTRA GABARITO HUMANO (400 trechos, 2026-09-01):

    sinal                      dispara   precisao   lift
    anafora orfa                23/400     100,0%   1,35x
    conectivo dependente        16/400      87,5%   1,18x
    combinado                   39/400      94,9%   1,28x

Base de acerto por chance: 74,0%.

Este modulo NAO depende de modelo, biblioteca nova ou GPU. E regex + regra de
posicao sobre a transcricao ja existente.
"""
from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# Listas lexicais. Fonte: Projeto NURC (marcadores discursivos do portugues
# falado), compiladas no relatorio fronteira-topico-2026-09-01.md secao 2.3.
# ---------------------------------------------------------------------------

# Abertura FORTE: sozinha ja indica inicio de novo topico.
ABERTURA_FORTE = (
    "agora sobre", "agora vamos", "mudando de assunto", "mudando um pouco",
    "e quanto a", "e sobre", "deixa eu te perguntar", "deixa eu perguntar",
    "queria te perguntar", "queria perguntar", "outra coisa", "outra pergunta",
    "proxima pergunta", "voltando a", "voltando ao", "sobre a questao",
    "a respeito de", "falando em", "falando sobre", "ja que voce falou",
    "aproveitando", "primeira pergunta", "ultima pergunta", "minha pergunta",
    "a minha pergunta",
)

# Palavras interrogativas iniciais. CRITICO: incluir a construcao 'QU- + que'
# ("onde que", "por que que"), que e 43% das interrogativas na FALA contra 1,1%
# na escrita (fronteira-topico secao 3.1). Um regex calibrado em portugues
# escrito perde quase metade das perguntas reais.
INTERROGATIVAS = (
    "como", "por que", "porque", "pra que", "para que", "o que", "que",
    "qual", "quais", "quando", "quem", "onde", "aonde", "quanto", "quanta",
    "quantos", "quantas", "sera que", "voce acha", "o senhor acha",
    "a senhora acha", "voce acredita", "o senhor considera",
)

# Vicios faticos. Regra de POSICAO, nao de semantica: em portugues falado estes
# itens sao mediais ou finais e NUNCA abrem turno. Se aparecem no inicio, nao e
# pergunta de entrevistador (fronteira-topico secao 4).
VICIO_FATICO = (
    "ne", "entendeu", "sabe", "certo", "ta", "viu", "entende", "percebe",
    "nao e", "nao acha", "concorda",
)

# Abertura protocolar/cerimonial: consome a janela de 2s que decide a retencao
# sem entregar conteudo (gancho-abertura secao A.3).
PROTOCOLAR = (
    "bom dia", "boa tarde", "boa noite", "seja bem vindo", "seja bem vinda",
    "sejam bem vindos", "seja muito bem vindo", "seja muito bem vinda",
    "obrigado pela pergunta", "obrigada pela pergunta",
    "antes de mais nada", "primeiro eu queria", "primeiramente",
    "eu queria agradecer", "gostaria de agradecer", "agradeco a",
    "muito obrigado", "muito obrigada", "com licenca", "senhoras e senhores",
)

# Conectivos que denunciam continuacao de raciocinio anterior. Usados apenas
# como sinal FRACO: em fala espontanea 'entao' e 'ai' sao muletas de
# planejamento, nao conectivos logicos (autossuficiencia secao 3).
CONECTIVO_DEPENDENTE = (
    "mas", "porem", "contudo", "entretanto", "porque", "pois", "por isso",
    "alem disso", "ou seja", "isto e", "portanto", "logo", "assim",
)

# Demonstrativo/anafora orfa: se abre o corte, aponta para fora dele.
ANAFORA_ABERTURA = (
    "isso", "isto", "aquilo", "esse", "essa", "esses", "essas", "este",
    "esta", "aquele", "aquela", "ele", "ela", "eles", "elas", "la", "ali",
    "como eu disse", "como eu falei", "como eu comentei", "que eu falei",
    "que eu disse", "o que eu falei", "conforme falei",
)

MAX_RECUO_S = 25.0
PAUSA_FRONTEIRA_S = 0.40


def _normalizar(texto: str) -> str:
    """Minusculas sem acento, para casar lista lexical contra fala transcrita."""
    if not texto:
        return ""
    plano = unicodedata.normalize("NFD", str(texto))
    plano = "".join(c for c in plano if unicodedata.category(c) != "Mn")
    # Hifen e pontuacao viram espaco: "bem-vinda" precisa casar com a lista
    # "bem vinda". Sem isto o detector deixava passar a abertura cerimonial da
    # coletiva (falha real pega no teste de 01/09).
    plano = re.sub(r"[-\u2013\u2014_/]+", " ", plano.lower())
    plano = re.sub(r"[^\w\s?]", " ", plano)
    return re.sub(r"\s+", " ", plano).strip()


def _comeca_com(texto_norm: str, termos):
    for termo in termos:
        if texto_norm == termo or texto_norm.startswith(termo + " "):
            return termo
    return None


def limpar_franja(texto_norm: str) -> str:
    """Remove muletas iniciais antes de testar o primeiro token.

    Sem isto, 'olha, por que o senhor...' nao casa como pergunta.
    """
    franja = ("olha", "bom", "bem", "entao", "e", "ah", "eh", "assim",
              "veja", "escuta", "poxa", "cara", "oh")
    # Nao descascar quando a muleta e, na verdade, o inicio de expressao
    # protocolar: "bom dia" nao e "bom" + "dia". Sem esta guarda, limpar_franja
    # engolia o "bom" e "bom dia a todos" deixava de ser protocolar.
    protegido = ("bom dia", "boa tarde", "boa noite", "bem vindo",
                 "bem vinda", "bem vindos", "bem vindas")
    anterior = None
    atual = texto_norm
    while atual != anterior:
        anterior = atual
        if any(atual.startswith(pref) for pref in protegido):
            break
        for f in franja:
            if atual.startswith(f + " ") or atual.startswith(f + ","):
                atual = atual[len(f):].lstrip(" ,").strip()
                break
    return atual


def eh_abertura_forte(texto: str) -> bool:
    """Marcador que sozinho ja sinaliza inicio de novo topico."""
    norm = limpar_franja(_normalizar(texto))
    return _comeca_com(norm, ABERTURA_FORTE) is not None


def eh_pergunta(texto: str) -> bool:
    """Detecta pergunta REAL em transcricao sem pontuacao confiavel.

    Regra de posicao para separar pergunta de vicio: 'ne?'/'entendeu?' nunca
    abrem turno em portugues falado.
    """
    norm = limpar_franja(_normalizar(texto))
    if not norm:
        return False

    palavras = norm.split()
    # Enunciado curto composto so de vicio fatico nao e pergunta.
    if len(palavras) <= 3 and _comeca_com(norm, VICIO_FATICO):
        return False

    if "?" in (texto or ""):
        return True

    if _comeca_com(norm, INTERROGATIVAS):
        return True

    # Pedido explicito de pergunta ("deixa eu te perguntar", "minha pergunta")
    # e pergunta de entrevistador mesmo sem palavra interrogativa inicial.
    if eh_abertura_forte(texto) and re.search(r"\bpergunt", norm):
        return True

    # Construcao QU- + que, tipica da fala: "onde que", "por que que".
    if re.match(r"^(o que|que|qual|quando|quem|onde|aonde|como|por que)\s+que\b", norm):
        return True

    return False


def eh_protocolar(texto: str) -> bool:
    """Abertura cerimonial que gasta a janela de retencao sem conteudo."""
    norm = limpar_franja(_normalizar(texto))
    if not norm:
        return False
    if _comeca_com(norm, PROTOCOLAR) is not None:
        return True
    # Vocativo institucional isolado e curto.
    if len(norm.split()) <= 4 and re.match(
        r"^(senhor|senhora|deputado|ministro|presidente|jornalista)\b", norm
    ):
        return True
    return False


def abre_dependente(texto: str):
    """Retorna o motivo se o texto abre preso ao que veio antes.

    Validado contra 400 trechos julgados: anafora orfa 100% de precisao,
    conectivo 87,5%, contra base de chance de 74,0%.
    """
    norm = limpar_franja(_normalizar(texto))
    if not norm:
        return None
    achado = _comeca_com(norm, ANAFORA_ABERTURA)
    if achado:
        return "anafora_orfa:%s" % achado
    achado = _comeca_com(norm, CONECTIVO_DEPENDENTE)
    if achado:
        return "conectivo_dependente:%s" % achado
    return None


FIM_FRAGMENTADO_BRANCO = (
    "ta", "e isso", "certo", "ne", "sabe", "entendeu", "viu", "ok",
    "perfeito", "show", "valeu", "obrigado", "obrigada", "beleza",
    "fim", "acabou", "pronto", "entao e isso", "muito obrigado",
    "muito obrigada", "ate mais", "ate logo", "tchau",
)


def fim_fragmentado(texto: str):
    """Retorna o motivo se o fim do texto e fragmentado/backchannel.

    Dado medido (bench_contexto.py, 2026-09-02): fim <15 chars e ruim
    (1,39% excelencia alto / 3,24% baixo), MAS backchannel e fecho legitimo
    tem 2,61% excelencia, acima da base. Lista branca obrigatoria.
    """
    norm = _normalizar(texto)
    if not norm:
        return None
    if len(norm) >= 15:
        return None
    if norm in FIM_FRAGMENTADO_BRANCO:
        return None
    return "fim_fragmentado"


def diagnosticar_saida(texto_final: str) -> dict:
    """Classifica a borda de saida de um corte.

    Espelha `diagnosticar_abertura`, mas para o FIM do bloco.
    """
    return {
        "fragmentado": fim_fragmentado(texto_final),
    }


def encontrar_inicio_do_assunto(blocos, indice_inicial, limite_recuo_s=MAX_RECUO_S):
    """Recua o inicio do corte ate onde o ASSUNTO comeca.

    Percorre para tras a partir de `indice_inicial` procurando, em ordem de
    prioridade, a fronteira real do topico. Nunca cruza abertura protocolar e
    nunca recua mais que `limite_recuo_s`.

    Retorna (novo_indice, diagnostico). O diagnostico e legivel por humano e
    entra no relatorio do corte, para que a decisao seja auditavel.
    """
    diag = {"aplicado": False, "motivo": "sem_fronteira_melhor",
            "indice_original": indice_inicial, "indice_novo": indice_inicial,
            "recuo_s": 0.0}

    if not blocos or indice_inicial <= 0 or indice_inicial >= len(blocos):
        diag["motivo"] = "sem_blocos_anteriores"
        return indice_inicial, diag

    try:
        t_ref = float(blocos[indice_inicial].get("start", 0) or 0)
    except (TypeError, ValueError):
        diag["motivo"] = "tempo_invalido"
        return indice_inicial, diag

    melhor_idx, melhor_motivo, melhor_prio = indice_inicial, None, 0

    for idx in range(indice_inicial - 1, -1, -1):
        bloco = blocos[idx]
        try:
            t_bloco = float(bloco.get("start", 0) or 0)
        except (TypeError, ValueError):
            continue

        if t_ref - t_bloco > limite_recuo_s:
            break

        texto = bloco.get("text") or ""

        # Barreira: nunca arrastar protocolo para dentro do corte.
        if eh_protocolar(texto):
            diag["barreira_protocolar"] = texto.strip()[:80]
            break

        # Prioridade 3 (maxima): a pergunta que originou a resposta.
        if eh_pergunta(texto):
            melhor_idx, melhor_motivo, melhor_prio = idx, "pergunta_de_origem", 3
            break

        # Prioridade 2: marcador explicito de novo topico.
        if melhor_prio < 2 and eh_abertura_forte(texto):
            melhor_idx, melhor_motivo, melhor_prio = idx, "abertura_de_topico", 2

        # Prioridade 1: pausa longa antes desta fala = fronteira natural.
        if melhor_prio < 1 and idx > 0:
            try:
                fim_anterior = float(blocos[idx - 1].get("end", 0) or 0)
                if t_bloco - fim_anterior >= PAUSA_FRONTEIRA_S:
                    melhor_idx, melhor_motivo, melhor_prio = idx, "pausa_longa", 1
            except (TypeError, ValueError):
                pass

    if melhor_motivo and melhor_idx < indice_inicial:
        try:
            recuo = t_ref - float(blocos[melhor_idx].get("start", 0) or 0)
        except (TypeError, ValueError):
            recuo = 0.0
        diag.update({
            "aplicado": True,
            "motivo": melhor_motivo,
            "indice_novo": melhor_idx,
            "recuo_s": round(recuo, 2),
            "texto_novo_inicio": (blocos[melhor_idx].get("text") or "").strip()[:100],
        })
        return melhor_idx, diag

    return indice_inicial, diag


def diagnosticar_abertura(texto_inicial: str) -> dict:
    """Classifica a abertura de um corte.

    Substitui as flags `context_complete`/`payoff_complete`, que marcavam 100%
    sempre -- decoracao, nao controle de qualidade.
    """
    return {
        "protocolar": eh_protocolar(texto_inicial),
        "dependente": abre_dependente(texto_inicial),
        "pergunta": eh_pergunta(texto_inicial),
        "abertura_topico": eh_abertura_forte(texto_inicial),
    }


def _palavras_conteudo(texto):
    """Palavras de conteudo (>=4 letras, sem palavra-vazia) para casar textos."""
    vazias = {
        "a", "as", "ao", "aos", "com", "da", "das", "de", "do", "dos", "e",
        "em", "esse", "essa", "isso", "na", "nas", "no", "nos", "o", "os",
        "por", "que", "se", "sem", "um", "uma", "uns", "umas", "para", "pra",
        "mais", "mas", "como", "quando", "sobre", "voce", "senhor", "senhora",
        "sua", "seu", "muito", "ja", "nao", "sim", "entao", "tambem", "ser",
    }
    norm = _normalizar(texto)
    return {p for p in re.findall(r"[a-z0-9]{4,}", norm) if p not in vazias}


def localizar_pergunta_de_origem(blocos, indice_inicial, trigger_question,
                                 limite_recuo_s=60.0, minimo_sobreposicao=0.34):
    """Localiza, POR TEXTO, onde a pergunta do acervo foi realmente feita.

    MOTIVO (medido 2026-09-01): `encontrar_inicio_do_assunto` recua por
    heuristica e para na ULTIMA frase interrogativa antes do trecho. Numa
    coletiva o reporter preambula bastante antes de perguntar, entao a heuristica
    para no fim da pergunta e o bloco do acervo comeca no inicio da fala dele --
    erro medido de +7 a +30s.

    Aqui a busca e dirigida: o acervo diz QUAL pergunta procurar
    (`trigger_question`, presente em 100% dos 18.075 trechos), e esta funcao acha
    onde ela comeca. Nao sofre do problema de "parar na pergunta errada" porque
    nao adivinha -- compara texto.

    Recuo maior (60s) e seguro aqui justamente porque o destino e verificado por
    conteudo, nao por heuristica.

    Retorna (indice, diagnostico).
    """
    diag = {"aplicado": False, "motivo": "sem_trigger_question",
            "indice_original": indice_inicial, "indice_novo": indice_inicial}

    if not trigger_question or not blocos or indice_inicial <= 0:
        return indice_inicial, diag

    alvo = _palavras_conteudo(trigger_question)
    if len(alvo) < 2:
        diag["motivo"] = "pergunta_curta_demais"
        return indice_inicial, diag

    try:
        t_ref = float(blocos[indice_inicial].get("start", 0) or 0)
    except (TypeError, ValueError):
        diag["motivo"] = "tempo_invalido"
        return indice_inicial, diag

    melhor_idx, melhor_score = None, 0.0

    for idx in range(indice_inicial - 1, -1, -1):
        bloco = blocos[idx]
        try:
            t_bloco = float(bloco.get("start", 0) or 0)
        except (TypeError, ValueError):
            continue
        if t_ref - t_bloco > limite_recuo_s:
            break

        texto = bloco.get("text") or ""
        if eh_protocolar(texto):
            diag["barreira_protocolar"] = texto.strip()[:80]
            break

        # Janela de 2 blocos: a pergunta costuma atravessar a fronteira de frase.
        janela = texto
        if idx + 1 < len(blocos):
            janela = texto + " " + (blocos[idx + 1].get("text") or "")

        presentes = _palavras_conteudo(janela)
        if not presentes:
            continue
        sobreposicao = len(alvo & presentes) / float(len(alvo))
        if sobreposicao > melhor_score:
            melhor_score, melhor_idx = sobreposicao, idx

    if melhor_idx is not None and melhor_score >= minimo_sobreposicao and melhor_idx < indice_inicial:
        try:
            recuo = t_ref - float(blocos[melhor_idx].get("start", 0) or 0)
        except (TypeError, ValueError):
            recuo = 0.0
        diag.update({
            "aplicado": True,
            "motivo": "pergunta_do_acervo_localizada",
            "indice_novo": melhor_idx,
            "recuo_s": round(recuo, 2),
            "sobreposicao": round(melhor_score, 3),
            "texto_novo_inicio": (blocos[melhor_idx].get("text") or "").strip()[:100],
        })
        return melhor_idx, diag

    diag["motivo"] = "pergunta_nao_localizada_no_audio"
    diag["melhor_sobreposicao"] = round(melhor_score, 3)
    return indice_inicial, diag

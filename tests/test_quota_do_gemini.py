"""Quota esgotada é da conta, não do lote — e o Furia tratava como se fosse do lote.

Medindo o caminho do Gemini pela primeira vez (a chave nunca existiu nesta
máquina), a sabatina da Band devolveu isto, cinco vezes seguidas:

    [Gemini] Lote 1/5...
    [Gemini] gemini-2.5-flash quota excedida. Tentando proximo modelo...
    [Gemini] Lote sem resposta. Ultimo erro: 429: You exceeded your current quota
    [Gemini] Lote 2/5...
    [Gemini] gemini-2.5-flash quota excedida. Tentando proximo modelo...
    ...
    [Gemini] Tentando Ollama como fallback...
    [NLP] Usando selecao local por contexto e palavras-chave.

O 429 diz que a conta acabou, não que aquele pedaço da transcrição é difícil.
Continuar para o lote seguinte é pedir de novo o que já foi negado: numa fonte de
1h21 são dezenas de lotes de requisições condenadas antes de o corte cair calado
no NLP básico.

Foi o campo `origem` da régua que pegou isso — a sabatina apareceu como
"gemini, nlp" quando o pedido tinha sido gemini. Sem ele, a linha teria entrado na
comparação como se fosse medida do modelo, e a conclusão sobre qual caminho corta
melhor teria saído errada.
"""

import re

import pytest

from modules.clip_selector import ClipSelector


class _Resposta:
    def __init__(self, status, payload=None, texto=""):
        self.status_code = status
        self._payload = payload or {}
        self.text = texto

    def json(self):
        return self._payload


QUOTA_ESGOTADA = {
    "error": {
        "message": (
            "You exceeded your current quota, please check your plan and billing "
            "details. For more information on this error, head to: "
            "https://ai.google.dev/gemini-api/docs/rate-limits."
        )
    }
}


def _blocos(seletor, quantos):
    blocos = []
    tempo = 0.0
    for indice in range(quantos):
        texto = f"Frase inteira número {indice} sobre o assunto do bloco."
        frases = [{
            "start": tempo, "end": tempo + 30.0, "text": texto,
            "speakers": [], "timing_confidence": 1.0,
        }]
        blocos.append(seletor._make_editorial_block(indice, tempo, tempo + 30.0, texto, frases))
        tempo += 30.0
    return blocos


@pytest.fixture
def contador(monkeypatch):
    """Conta quantas requisições saíram, todas devolvendo 429."""
    chamadas = []

    def falso_post(url, **kwargs):
        chamadas.append(url)
        return _Resposta(429, QUOTA_ESGOTADA)

    import modules.clip_selector as modulo

    monkeypatch.setattr(modulo.requests, "post", falso_post)
    monkeypatch.setattr("time.sleep", lambda *_: None)
    return chamadas


def test_quota_esgotada_interrompe_os_lotes_seguintes(contador, monkeypatch):
    """Uma vez negada a conta, os outros lotes não são pedidos."""
    seletor = ClipSelector(max_clips=12, min_duration=20, max_duration=480)
    seletor.GEMINI_BLOCKS_PER_REQUEST = 8
    blocos = _blocos(seletor, 40)  # cinco lotes
    monkeypatch.setattr(seletor, "_build_transcript_blocks", lambda *a, **k: blocos)

    avisos = []
    seletor._select_with_gemini(
        [s for b in blocos for s in b["sentences"]], [], "",
        {"gemini_api_key": "x"},
        lambda mensagem, nivel="info": avisos.append(mensagem),
    )

    lotes_pedidos = sum(1 for a in avisos if re.match(r"\[Gemini\] Lote \d+/", a))
    assert lotes_pedidos == 1, (
        f"pediu {lotes_pedidos} lotes depois de a conta ser negada; quota "
        f"esgotada é da conta, não do lote"
    )


def test_a_quota_esgotada_e_dita_em_voz_alta(contador, monkeypatch):
    """O editor precisa saber que a corrida caiu, e por quê.

    A queda para o NLP era silenciosa: no log ela aparecia como cinco avisos de
    lote e uma linha de NLP, sem nunca dizer "a sua conta do Gemini acabou".
    """
    seletor = ClipSelector(max_clips=12, min_duration=20, max_duration=480)
    seletor.GEMINI_BLOCKS_PER_REQUEST = 8
    blocos = _blocos(seletor, 40)
    monkeypatch.setattr(seletor, "_build_transcript_blocks", lambda *a, **k: blocos)

    avisos = []
    seletor._select_with_gemini(
        [s for b in blocos for s in b["sentences"]], [], "",
        {"gemini_api_key": "x"},
        lambda mensagem, nivel="info": avisos.append(mensagem),
    )

    juntos = " | ".join(avisos).lower()
    assert "quota" in juntos
    assert any(
        marca in juntos for marca in ("acabou", "esgotad", "interromp")
    ), f"a queda saiu sem explicar o motivo: {avisos}"


def test_erro_comum_de_lote_nao_interrompe_os_outros(monkeypatch):
    """O controle: um lote que falha por outro motivo não cancela a corrida.

    Só a quota é da conta. Um timeout, uma resposta vazia ou um JSON ilegível
    valem para aquele lote e os seguintes continuam — era assim antes e continua.
    """
    seletor = ClipSelector(max_clips=12, min_duration=20, max_duration=480)
    seletor.GEMINI_BLOCKS_PER_REQUEST = 8
    blocos = _blocos(seletor, 40)
    monkeypatch.setattr(seletor, "_build_transcript_blocks", lambda *a, **k: blocos)

    import modules.clip_selector as modulo

    monkeypatch.setattr(modulo.requests, "post", lambda url, **k: _Resposta(500, {}, "erro interno"))
    monkeypatch.setattr("time.sleep", lambda *_: None)

    avisos = []
    seletor._select_with_gemini(
        [s for b in blocos for s in b["sentences"]], [], "",
        {"gemini_api_key": "x"},
        lambda mensagem, nivel="info": avisos.append(mensagem),
    )
    lotes_pedidos = sum(1 for a in avisos if re.match(r"\[Gemini\] Lote \d+/", a))
    assert lotes_pedidos == 5, (
        f"pediu {lotes_pedidos} de 5 lotes; falha comum de lote não pode cancelar "
        f"a corrida inteira"
    )

"""A legenda do programa inteiro, colada num recorte do programa.

O editor tem um vídeo de 31min03 que é a sabatina tirada de uma transmissão de
1h07. A legenda que ele consegue vem do stream inteiro, então a sabatina começa
em 36:04 e todo timestamp cai depois do fim do arquivo. O programa respondia
"provavelmente pertence a outro vídeo" e recusava a importação — duas vezes, sem
saída, e a segunda nem apareceu no log, só num popup.

É o mesmo material com o relógio da transmissão. O que separa esse caso de uma
legenda genuinamente errada não é o deslocamento, é a extensão: se o material
cabe na duração do vídeo, é recorte deslocado; se não cabe, é outro vídeo.
"""

from app import _realign_offset_transcription, _transcription_coverage_report


DURACAO = 1863.0          # 31min03 de sabatina
ABERTURA = 2164.0         # 36:04, onde ela começa na transmissão de 1h07


def _legenda(primeiro, ultimo, passo=30.0, origem="manual"):
    segmentos, t = [], primeiro
    while t < ultimo:
        segmentos.append({"start": t, "end": min(t + passo, ultimo), "text": "Fala do candidato."})
        t += passo
    return {"segments": segmentos, "source": origem, "language": "pt"}


def test_recorte_com_o_relogio_da_transmissao_e_realinhado():
    legenda = _legenda(ABERTURA, ABERTURA + DURACAO)
    deslocamento = _realign_offset_transcription(legenda, DURACAO)

    assert abs(deslocamento - ABERTURA) < 0.1, "o deslocamento não foi reconhecido"
    assert abs(legenda["segments"][0]["start"]) < 0.1
    assert legenda["segments"][-1]["end"] <= DURACAO + 0.1
    assert _transcription_coverage_report(legenda, DURACAO)["status"] == "covered", (
        "depois de realinhada a legenda ainda é tratada como de outro vídeo"
    )


def test_o_deslocamento_aplicado_fica_registrado():
    """Um realinhamento errado move toda borda da fonte; ele tem de ser visível."""
    legenda = _legenda(ABERTURA, ABERTURA + DURACAO)
    _realign_offset_transcription(legenda, DURACAO)
    assert abs(legenda["timeline_rebased_s"] - ABERTURA) < 0.1


def test_a_legenda_do_programa_inteiro_continua_recusada():
    """1h07 de material num vídeo de 31min é outro vídeo, não um recorte."""
    legenda = _legenda(0.0, 4025.0)
    assert _realign_offset_transcription(legenda, DURACAO) == 0.0
    assert _transcription_coverage_report(legenda, DURACAO)["status"] == "mismatch_suspected"


def test_legenda_que_ja_bate_nao_e_tocada():
    legenda = _legenda(0.0, DURACAO)
    antes = [dict(s) for s in legenda["segments"]]
    assert _realign_offset_transcription(legenda, DURACAO) == 0.0
    assert legenda["segments"] == antes


def test_um_trecho_curto_deslocado_nao_e_esticado_para_a_fonte_toda():
    """Dois minutos de legenda não são um recorte de trinta e um minutos.

    Realinhar aqui alinharia o começo e erraria tudo depois; é um caso para
    recusar, não para adivinhar.
    """
    legenda = _legenda(ABERTURA, ABERTURA + 120.0)
    assert _realign_offset_transcription(legenda, DURACAO) == 0.0


def test_transcricao_automatica_nao_e_realinhada():
    """Whisper e Gemini leem o próprio arquivo; um desvio ali é defeito real."""
    legenda = _legenda(ABERTURA, ABERTURA + DURACAO, origem="whisper")
    assert _realign_offset_transcription(legenda, DURACAO) == 0.0

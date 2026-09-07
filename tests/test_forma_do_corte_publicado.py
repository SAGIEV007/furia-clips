"""A forma dos cortes que a equipe publicou de verdade.

A PERGUNTA DO EDITOR QUE ORIGINOU ISTO
--------------------------------------
    "além de eu enviar cortes prontos (...) através dos cortes do Renan que já
     estão no Instagram"

Ele estava certo, e o teste mais importante deste arquivo é o que registra o
LIMITE: dá para aprender a forma do corte publicado, não a hora dele no vídeo
longo. O Renan repete as teses em vários vídeos com palavras diferentes, então
procurar o texto publicado dentro de uma live acha o argumento, não a gravação.
Um gabarito com a hora errada ensina o motor a cortar errado com confiança.
"""

import json

import pytest

from modules.forma_publicada import forma, legenda_saiu_do_corte, ler, medir


def _corte(url, caption, falas):
    return {"url": url, "caption": caption, "script": [
        {"startS": a, "endS": b, "speaker": s, "text": t} for a, b, s, t in falas
    ]}


def test_a_duracao_sai_da_transcricao_sem_alinhar_nada():
    """A forma não precisa saber de que minuto do vídeo longo o corte saiu."""
    f = forma(_corte("u", "c", [
        (0.6, 2.05, "unknown", "Que Brasil que você vai pegar ano que vem?"),
        (2.05, 92.08, "renan", "Eu vou pegar um Brasil destruído."),
    ]))
    assert f["duracao_s"] == pytest.approx(91.5, abs=0.1)


def test_abrir_na_pergunta_curta_do_reporter_e_reconhecido():
    """O corte mais visto de todos (9,1 M) abre com 1,5 s de pergunta.

    Isso não é exceção, é padrão de campeão — e confirma a regra que o editor
    deu: "se for uma pergunta curta do repórter não tem problema mostrar".
    """
    f = forma(_corte("u", "c", [
        (0.6, 2.05, "unknown", "Que Brasil que você vai pegar ano que vem?"),
        (2.05, 92.0, "renan", "Eu vou pegar um Brasil destruído."),
    ]))
    assert f["abre_em_outro"] is True
    assert f["abertura_curta"] is True, "1,5 s de pergunta é abertura curta"


def test_abertura_longa_de_outro_nao_conta_como_curta():
    """A pergunta de dois minutos é o defeito que o editor mandou aparar."""
    f = forma(_corte("u", "c", [
        (0.0, 45.0, "unknown", "Uma pergunta longuíssima do jornalista."),
        (45.0, 120.0, "renan", "A resposta."),
    ]))
    assert f["abre_em_outro"] is True
    assert f["abertura_curta"] is False


def test_a_legenda_que_repete_uma_frase_do_corte():
    """A única evidência de headline que existe sem o editor escrever nada.

    Dois testes de estilo de headline estão parados esperando exemplos dele.
    A legenda do post publicado é um exemplo aprovado por construção: alguém
    escolheu aquela frase para vender aquele corte.
    """
    f = forma(_corte("u", "Que Brasil vou pegar ano que vem?", [
        (0.6, 2.05, "unknown", "Que Brasil que você vai pegar ano que vem?"),
        (2.05, 92.0, "renan", "Eu vou pegar um Brasil destruído."),
    ]))
    assert legenda_saiu_do_corte(f) is True


def test_legenda_de_marketing_nao_conta():
    """"Siga @renansantosmbl" não é headline do corte."""
    f = forma(_corte("u", "Siga @renansantosmbl", [
        (0.0, 30.0, "renan", "Uma tese completamente diferente sobre outra coisa."),
    ]))
    assert legenda_saiu_do_corte(f) is False


def test_medir_resume_o_conjunto():
    cortes = [
        _corte("a", "x", [(0.0, 52.0, "renan", "Curto.")]),
        _corte("b", "y", [(0.0, 92.0, "renan", "Médio.")]),
        _corte("c", "z", [(0.0, 127.0, "renan", "Longo.")]),
    ]
    numeros = medir(cortes)
    assert numeros["n"] == 3
    assert numeros["duracao_mediana_s"] == 92.0
    assert numeros["duracao_min_s"] == 52.0
    assert numeros["duracao_max_s"] == 127.0


def test_sem_cortes_no_disco_nao_quebra(tmp_path, monkeypatch):
    """Primeiro dia numa máquina nova: a pasta não existe, e isso é normal."""
    monkeypatch.setenv("FURIA_CLIPS_DATA_DIR", str(tmp_path))
    assert ler() == []
    assert medir([]) == {"n": 0}


def test_corte_sem_falas_e_ignorado():
    assert forma({"url": "u", "caption": "c", "script": []}) == {}


def test_o_limite_esta_escrito_onde_alguem_vai_ler():
    """O que esta régua NÃO faz precisa estar dito, senão alguém tenta de novo.

    Sem este aviso, a próxima sessão — minha, de outro modelo, ou do Hermes —
    tenta alinhar corte publicado com vídeo longo, acha que deu certo, e produz
    gabarito com hora errada. Isso é pior que não ter gabarito.
    """
    from pathlib import Path

    fonte = (Path(__file__).resolve().parents[1] / "modules" / "forma_publicada.py").read_text(
        encoding="utf-8"
    )
    assert "não bate" in fonte or "não dá para tirar" in fonte.lower()
    assert "78 blocos" in fonte, "a evidência do teste que falhou tem que ficar escrita"


def test_o_formato_do_chub_e_lido_como_vem(tmp_path, monkeypatch):
    """O arquivo salvo é a resposta do CHUB, sem conversão pelo caminho.

    Converter na entrada é onde se perde campo sem ninguém notar; aqui o que
    está no disco é o que o CHUB devolveu.
    """
    monkeypatch.setenv("FURIA_CLIPS_DATA_DIR", str(tmp_path))
    destino = tmp_path / "publicados"
    destino.mkdir(parents=True)
    (destino / "a.json").write_text(json.dumps({
        "channel": "@renansantosmbl", "url": "https://x/a", "caption": "Uma tese",
        "script": [{"startS": 0.0, "endS": 60.0, "speaker": "renan", "text": "Uma tese."}],
    }), encoding="utf-8")

    cortes = ler()
    assert len(cortes) == 1
    assert medir(cortes)["duracao_mediana_s"] == 60.0

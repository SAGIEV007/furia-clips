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


# ── a distância mínima entre viradas de assunto ─────────────────────────────


def test_a_distancia_minima_entre_viradas_e_em_segundos():
    """O teto mecânico que impedia o Furia de ver quatro dos dez assuntos.

    `min_sentences` fazia dois trabalhos: decidir se havia material para
    segmentar, e servir de distância mínima entre duas viradas. O segundo uso
    era um proxy ruim — medido na sabatina, 4 dos 10 blocos do Acervo têm menos
    de 32 frases, e o menor tem 11. Com 32 frases de distância obrigatória eles
    eram impossíveis por construção.

    Este teste trava a regra em segundos. Se alguém voltar a contar em frases, a
    leitura de assunto cai de 3/9 para 1/9 sem nenhum erro aparecer na tela.
    """
    from modules.topic_segmenter import _boundaries

    # Um vale de coesão em duas posições próximas em índice, mas distantes no
    # relógio: é o caso do bloco curto do Acervo.
    curva = [0.9, 0.9, 0.1, 0.9, 0.9, 0.1, 0.9, 0.9]
    tempos = [0.0, 40.0, 80.0, 120.0, 160.0, 200.0, 240.0, 280.0]

    so_frases = _boundaries(curva, min_gap=32)
    com_tempo = _boundaries(curva, min_gap=32, tempos=tempos, min_gap_s=15.0)

    assert len(so_frases) == 1, "contando frases, a segunda virada é impossível"
    assert len(com_tempo) == 2, "contando segundos, as duas cabem"


def test_sem_tempos_o_comportamento_antigo_continua():
    """Quem chama sem os tempos não muda de comportamento."""
    from modules.topic_segmenter import _boundaries

    curva = [0.9, 0.1, 0.9, 0.1, 0.9]
    assert _boundaries(curva, min_gap=3) == _boundaries(curva, min_gap=3, tempos=None)


def test_o_limite_nunca_fica_abaixo_do_alcancavel():
    """O defeito que fazia uma live de duas horas virar um bloco só.

    `média − desvio` supõe que a coesão varia pouco em torno da média. Numa
    entrevista vale; numa live não. Medido na live do Ceará (234 min):

        média 0,093 · desvio 0,100 · limite -0,007

    Coesão não é negativa, então NENHUM ponto podia passar — as duas horas
    viravam um bloco só e a régua marcava 0 de 4 viradas achadas. Com o piso no
    décimo percentil: 4 de 4, e as outras quatro fontes medidas não mudaram uma
    vírgula.

    Se alguém tirar o piso, a live volta a 0/4 sem nenhum erro na tela.
    """
    from modules.topic_segmenter import _boundaries

    # Uma curva como a da live: muitos zeros, então o desvio supera a média e
    # `média − desvio` fica negativo.
    curva = [0.0, 0.5, 0.0, 0.6, 0.0, 0.5, 0.0, 0.6, 0.0, 0.5]
    achadas = _boundaries(curva, min_gap=2)

    assert achadas, (
        "com o limite negativo nada passava e a live inteira virava um bloco só"
    )


# ── a porta da troca de voz ─────────────────────────────────────────────────


def test_so_vale_de_fronteira_onde_alguem_troca_de_vez():
    """O que levou a precisão de 18% para 30% nas cinco fontes.

    Vale de coesão sozinho não distingue virada de assunto de variação normal
    de vocabulário: 18% das fronteiras propostas eram reais. Nas cinco fontes
    com gabarito do Acervo, 34 das 39 viradas (87%) caem a menos de 15 s de uma
    troca de locutor. A troca sozinha também não serve — são 395 trocas para 39
    viradas — mas serve de porta.
    """
    from modules.topic_segmenter import _boundaries

    # Dois vales iguais; só o segundo cai onde alguém trocou de vez.
    curva = [0.9, 0.9, 0.1, 0.9, 0.9, 0.1, 0.9, 0.9]
    tempos = [0.0, 40.0, 80.0, 120.0, 160.0, 200.0, 240.0, 280.0]

    sem_porta = _boundaries(curva, min_gap=2, tempos=tempos, min_gap_s=15.0)
    com_porta = _boundaries(
        curva, min_gap=2, tempos=tempos, min_gap_s=15.0,
        # a fronteira do vale em `i` cai em tempos[i + 1]: o vale em 5 cai aos
        # 240 s e tem marca em cima; o vale em 2 cai aos 120 s e não tem
        trocas_de_voz=[3.0, 239.0, 300.0],
    )

    assert len(sem_porta) == 2, "sem a porta, os dois vales viram fronteira"
    assert com_porta == [5], "com a porta, só o vale que cai numa troca de voz"


def test_sem_diarizacao_a_porta_nao_fecha_o_programa():
    """Material sem locutor identificado não pode sair com zero fronteiras.

    A porta é uma peneira; peneira sem nada para peneirar tem que deixar passar.
    Sem esta trava, uma transcrição sem marca de locutor — que existe — viraria
    um bloco só, que é exatamente o defeito que a live já teve uma vez.
    """
    from modules.topic_segmenter import _boundaries

    curva = [0.9, 0.9, 0.1, 0.9, 0.9, 0.1, 0.9, 0.9]
    tempos = [0.0, 40.0, 80.0, 120.0, 160.0, 200.0, 240.0, 280.0]
    sem_porta = _boundaries(curva, min_gap=2, tempos=tempos, min_gap_s=15.0)

    # Nenhuma marca, e marcas de menos para confiar: nos dois casos o resultado
    # é o de sempre.
    assert _boundaries(curva, min_gap=2, tempos=tempos, min_gap_s=15.0,
                       trocas_de_voz=[]) == sem_porta
    assert _boundaries(curva, min_gap=2, tempos=tempos, min_gap_s=15.0,
                       trocas_de_voz=[10.0, 20.0]) == sem_porta


def test_porta_que_nao_deixa_ninguem_passar_e_ignorada():
    """Diarização que erra todos os instantes não pode zerar a leitura."""
    from modules.topic_segmenter import _boundaries

    curva = [0.9, 0.9, 0.1, 0.9, 0.9, 0.1, 0.9, 0.9]
    tempos = [0.0, 40.0, 80.0, 120.0, 160.0, 200.0, 240.0, 280.0]

    achadas = _boundaries(
        curva, min_gap=2, tempos=tempos, min_gap_s=15.0,
        trocas_de_voz=[1.0, 2.0, 3.0],  # nenhuma perto de um vale
    )
    assert achadas == _boundaries(curva, min_gap=2, tempos=tempos, min_gap_s=15.0)


def test_os_dois_formatos_de_marca_de_troca_entram():
    """A marca chega de dois jeitos conforme o caminho da transcrição.

    Pelo motor, `_build_sentences` guarda o instante exato em
    `speaker_change_at` — uma frase montada pode ter mais de um. Por outros
    caminhos vem `speaker_change` na frase, e aí o instante é o começo dela. Se
    só um formato fosse lido, a porta ficaria fechada sem ninguém notar: o
    número não some, ele só volta a ser 18%.
    """
    from modules.topic_segmenter import _instantes_de_troca

    lidos = _instantes_de_troca([
        {"start": 0.0, "speaker_change_at": [12.5, 20.0]},
        {"start": 33.0, "speaker_change": True},
        {"start": 40.0},
        {"start": 50.0, "speaker_change_at": ["nao é número"]},
    ])
    assert lidos == [12.5, 20.0, 33.0]


def test_ordenar_por_vale_mais_fundo_ficou_registrado_como_tentado():
    """A tentativa que não deu certo tem que estar escrita, com o número.

    Sem isto, a próxima sessão tenta profundidade de vale de novo achando que é
    ideia nova. Foi medida: 7/39 achadas com 23% de precisão, contra 25/39 com
    18%. Quase não separa vale verdadeiro de falso.
    """
    from pathlib import Path

    fonte = (Path(__file__).resolve().parents[1] / "modules" / "topic_segmenter.py").read_text(
        encoding="utf-8"
    )
    assert "_profundidade_do_vale" in fonte
    assert "não resolveu" in fonte.lower() or "nao resolveu" in fonte.lower()

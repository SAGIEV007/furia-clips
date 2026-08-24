"""O Whisper adivinhava os nomes próprios, e o léxico do projeto ficava de fora.

O `data/lexico/entidades_chub.json` diz o problema na própria nota:

    'Nicolas Ferreira' aparece mais vezes que 'Nikolas Ferreira', e a forma rara
    é a certa.

Um reconhecedor escolhe a forma frequente. Corrigir depois — que é o que
`_revise_captions` faz — conserta a grafia, mas só onde alguém já vouchou pelo
nome, e nunca recupera o que virou outra palavra: "Kataguiri" ouvido como "cata
guiri" não é erro de grafia, é erro de segmentação, e nenhuma tabela de troca
alcança isso.

O Whisper aceita `initial_prompt` justamente para isso: um texto que enviesa o
decodificador antes de ele decidir. Ele não era usado em lugar nenhum.

Duas coisas este arquivo guarda. A primeira é que o viés sai do léxico e respeita
o contrato que já existe — `confirmado=false` nunca entra, porque entrar seria
corrigir em silêncio pelo caminho de trás. A segunda é o modo de falha conhecido:
um `initial_prompt` pode ser ecoado pelo próprio reconhecedor e aparecer como
primeira legenda do vídeo. Isso vira uma citação falsa, que é o erro mais caro
que este projeto pode cometer.
"""

import pytest

from modules.transcriber import Transcriber


def test_o_vies_sai_dos_nomes_confirmados_do_lexico():
    prompt = Transcriber()._vocabulary_prompt()
    assert prompt, "nenhum viés de vocabulário foi montado"
    assert "Renan Santos" in prompt
    assert "MBL" in prompt or "Missão" in prompt


def test_nome_nao_confirmado_nunca_entra_no_vies():
    """O contrato do léxico: `confirmado=false` no máximo sinaliza.

    Enviesar o reconhecedor para uma grafia que ninguém aprovou é corrigir em
    silêncio pela porta dos fundos — pior que corrigir depois, porque não deixa
    rastro em `conferir_no_audio`.
    """
    import json
    import pathlib

    caminho = pathlib.Path("data/lexico/entidades_chub.json")
    if not caminho.exists():
        pytest.skip("léxico ausente")
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    confirmados = {
        str(e.get("canonico") or "") for e in dados["entradas"] if e.get("confirmado")
    }
    prompt = Transcriber()._vocabulary_prompt()
    # A lista escolhida, e não uma varredura por substring: "Flávio" é parte de
    # "Flávio Bolsonaro" e apareceria como intruso sem nunca ter sido escolhido.
    _, _, assunto = prompt.partition("falando sobre ")
    escolhidos = [nome.strip(" .") for nome in assunto.split(",") if nome.strip(" .")]
    assert escolhidos, "o viés não escolheu nome nenhum"
    intrusos = [nome for nome in escolhidos if nome not in confirmados]
    assert not intrusos, f"nomes não confirmados entraram no viés: {intrusos}"


def test_o_vies_cabe_na_janela_do_whisper():
    """O `initial_prompt` tem janela curta; estourar degrada em vez de ajudar.

    São 337 entradas no léxico. Enfiar todas seria trocar um erro de nome por um
    reconhecedor pior no vídeo inteiro.
    """
    prompt = Transcriber()._vocabulary_prompt()
    assert len(prompt) <= Transcriber.VOCABULARY_PROMPT_MAX_CHARS


def test_o_vies_e_uma_frase_e_nao_uma_lista():
    """Lista de nomes solta faz o Whisper repetir; frase natural, não.

    O `initial_prompt` também modela o estilo do que vem depois — inclusive a
    pontuação, que é o que separa uma legenda utilizável de um bloco de 128
    palavras sem um ponto final.
    """
    prompt = Transcriber()._vocabulary_prompt()
    assert prompt.rstrip().endswith("."), f"o viés não é uma frase fechada: {prompt!r}"
    assert prompt.count(",") >= 2, "sem vírgula nenhuma isso é uma lista, não uma frase"


# ── o modo de falha do próprio recurso ─────────────────────────────────────

def test_o_prompt_ecoado_pelo_reconhecedor_e_descartado():
    """Whisper às vezes devolve o `initial_prompt` como se fosse fala.

    Isso vira a primeira legenda do vídeo, entra no corte, e pode virar aspas
    numa headline — uma citação de algo que ninguém disse. É o erro mais caro que
    este projeto pode cometer, e ele nasceria de um recurso que existe para
    melhorar a transcrição.
    """
    transcritor = Transcriber()
    vies = transcritor._vocabulary_prompt()
    resultado = {
        "segments": [
            {"id": 0, "start": 0.0, "end": 4.0, "text": vies, "words": []},
            {"id": 1, "start": 4.2, "end": 9.0, "text": "Boa tarde a todos.", "words": []},
        ],
        "full_text": f"{vies} Boa tarde a todos.",
    }
    transcritor._drop_echoed_prompt(resultado)
    textos = [s["text"] for s in resultado["segments"]]
    assert vies not in textos, "o viés foi ecoado e virou legenda"
    assert "Boa tarde a todos." in textos
    assert vies not in resultado["full_text"]


def test_fala_de_verdade_parecida_com_o_vies_nao_e_descartada():
    """O controle: ele fala esses nomes o tempo todo — é o assunto dele.

    Só o eco literal do prompt sai, e só se estiver na abertura. Uma frase que
    apenas cita os mesmos nomes é fala de verdade e fica.
    """
    transcritor = Transcriber()
    resultado = {
        "segments": [
            {"id": 0, "start": 0.0, "end": 6.0,
             "text": "O Renan Santos falou do MBL e do Partido Missão ontem.", "words": []},
        ],
        "full_text": "O Renan Santos falou do MBL e do Partido Missão ontem.",
    }
    transcritor._drop_echoed_prompt(resultado)
    assert len(resultado["segments"]) == 1, "descartou fala de verdade"


def test_eco_no_meio_do_video_nao_e_tocado():
    """Fora da abertura não é eco de prompt; é outra coisa, e mexer seria adivinhar."""
    transcritor = Transcriber()
    vies = transcritor._vocabulary_prompt()
    resultado = {
        "segments": [
            {"id": 0, "start": 0.0, "end": 5.0, "text": "Boa tarde a todos.", "words": []},
            {"id": 1, "start": 300.0, "end": 306.0, "text": vies, "words": []},
        ],
        "full_text": f"Boa tarde a todos. {vies}",
    }
    transcritor._drop_echoed_prompt(resultado)
    assert len(resultado["segments"]) == 2


def test_o_vies_pode_ser_desligado():
    """Um recurso que às vezes piora precisa de interruptor.

    `initial_prompt` é conhecido por induzir repetição em alguns áudios. Sem
    poder desligar, um vídeo estragado não teria como ser recuperado sem editar
    código.
    """
    assert Transcriber(vocabulary_bias=False)._vocabulary_prompt() == ""

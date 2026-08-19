"""The audio measurement reaching the decision it was measured for.

The energy profile was computed for every source — 4.418 windows on the
73-minute press conference of 18/08/2026 — passed into the Gemini and Ollama
selectors, and read by neither. Only the keyword fallback ever looked at it, so
the measurement only mattered on the path taken when everything else had already
failed.

Where the voice rises is the signal the editor keeps asking for by another name:
the "coice", the moment somebody is cornered. It now travels into the prompt.
"""

from modules.clip_selector import ClipSelector


def _blocks():
    return [
        {"index": 0, "start": 0.0, "end": 10.0, "duration": 10, "text": "Abertura calma."},
        {"index": 1, "start": 10.0, "end": 20.0, "duration": 10, "text": "Ele levanta a voz aqui."},
        {"index": 2, "start": 20.0, "end": 30.0, "duration": 10, "text": "E volta ao tom normal."},
    ]


def _perfil(valores, janela=1.0):
    """O formato que o AudioAnalyzer realmente devolve.

    Este teste passava com uma lista de números soltos — formato que a produção
    nunca produziu. O analisador devolve uma janela por segundo como dicionário,
    e ler isso como número derrubou o corte inteiro por dois dias: `float()`
    sobre um dicionário levanta TypeError, e o job morria em "Erro no corte"
    logo depois de dividir a transcrição.

    Uma fixture que não é o que a produção gera não prova nada.
    """
    return [
        {
            "time": round(indice * janela, 3),
            "energy_rms": round(valor, 6),
            "energy_db": round(valor, 2),
            "energy_normalized": round(valor, 4),
        }
        for indice, valor in enumerate(valores)
    ]


# Mediana 1.0; o bloco do meio sobe bem acima dela e o primeiro fica abaixo.
PROFILE = _perfil([0.4] * 10 + [1.0] * 5 + [2.4] * 5 + [1.0] * 10)


def test_a_raised_voice_is_marked():
    marked = ClipSelector._mark_energy(_blocks(), PROFILE)

    assert marked[1]["energy_mark"] == "voz elevada"


def test_a_quiet_stretch_is_marked_too():
    marked = ClipSelector._mark_energy(_blocks(), PROFILE)

    assert marked[0]["energy_mark"] == "voz baixa"


def test_an_ordinary_stretch_gets_no_mark():
    """Marking everything would be the same as marking nothing."""
    marked = ClipSelector._mark_energy(_blocks(), PROFILE)

    assert "energy_mark" not in marked[2]


def test_the_mark_reaches_the_prompt():
    selector = ClipSelector(target_duration=45, max_clips=10, min_duration=20, max_duration=600)
    marked = ClipSelector._mark_energy(_blocks(), PROFILE)

    prompt = selector._build_gemini_prompt(marked, "", None)

    assert "[voz elevada]" in prompt


def test_no_audio_is_not_an_error():
    assert "energy_mark" not in ClipSelector._mark_energy(_blocks(), None)[1]
    assert "energy_mark" not in ClipSelector._mark_energy(_blocks(), [])[1]


def test_um_perfil_estranho_nao_derruba_o_corte():
    """O que faltou: qualquer coisa inesperada aqui não pode matar o job.

    Marcar energia é enfeite editorial. O corte tem de sair mesmo que o áudio
    não tenha sido medido, tenha sido medido errado ou venha noutro formato.
    """
    for perfil in ([{"sem": "energia"}], ["texto"], [None], [{"time": None, "energy_rms": None}]):
        assert ClipSelector._mark_energy(_blocks(), perfil) is not None


def test_the_comparison_is_relative_to_the_source():
    """A studio and a street have different floors; an absolute level travels badly."""
    loud_room = _perfil([item["energy_normalized"] * 50 for item in PROFILE])

    assert ClipSelector._mark_energy(_blocks(), loud_room)[1]["energy_mark"] == "voz elevada"


def test_a_selecao_inteira_roda_com_o_perfil_de_producao():
    """O teste que faltava, e que teria pegado a quebra no mesmo dia.

    Provar a função isolada não bastou: o defeito só aparecia quando a seleção
    inteira rodava com o que o AudioAnalyzer devolve de verdade. Foram dois dias
    com o corte morto em "Erro no corte" e uma suíte inteira verde.
    """
    perfil = [
        {"time": float(i), "energy_rms": 0.05, "energy_db": -26.0, "energy_normalized": 0.5}
        for i in range(300)
    ]
    transcricao = {"segments": [
        {"start": i * 6.0, "end": i * 6.0 + 5.5,
         "text": f"Frase completa número {i} com assunto próprio e uma conclusão clara."}
        for i in range(50)
    ]}

    seletor = ClipSelector(target_duration=45, max_clips=10, min_duration=20, max_duration=600)
    clips = seletor.select_clips(transcricao, energy_profile=perfil, settings={"ai_backend": "nlp"})

    assert clips, "a seleção não devolveu candidato nenhum"

"""Regressão: orador único em palco deve permitir reframe 9:16.

Bug medido em 31/08 na live de MG (Renan Santos, 80 min, palco com plateia).

O clip 779s-843s passava em TRÊS dos quatro critérios de estabilidade:

    coverage           0.681  (mínimo 0.60)  OK
    average_confidence 0.664  (mínimo 0.60)  OK
    largest_jump       0.069  (máximo 0.30)  OK
    multiple_face_samples  1  (exigia == 0)  REPROVA

Bastava UM frame de oito com um rosto de plateia ao fundo para reprovar o
segmento inteiro. Sem `confident=True`, `plan_layout` devolve
`reframe_allowed=False`, `video_cutter` joga o índice em
`original_aspect_indices` e renderiza com `vertical=False` — 1920x1080, inútil
para Instagram.

Correção: o critério virou uma PROPORÇÃO (`max_multi_face_ratio=0.30`), que
tolera plateia ocasional mas continua reprovando debate real.
"""

from modules.face_tracker import FaceTracker


def _amostras(n, *, indices_multi=(), confidence=0.664, t0=779.0, passo=5.5):
    """Gera posições faciais sintéticas com controle de quais têm 2+ rostos."""
    return [
        {
            "time": t0 + i * passo,
            "center_x": 0.5 + i * 0.008,   # movimento suave, sem troca de câmera
            "center_y": 0.4,
            "confidence": confidence,
            "face_count": 2 if i in indices_multi else 1,
        }
        for i in range(n)
    ]


def test_plateia_ocasional_nao_reprova_orador_unico():
    """Reproduz o clip real 779s-843s: 1 de 8 amostras com plateia."""
    tracker = FaceTracker()
    avaliacao = tracker.assess_segment_tracking(
        _amostras(8, indices_multi=(3,)), 779, 843
    )

    assert avaliacao["confident"] is True, (
        "regressão: um único frame com plateia voltou a reprovar o segmento "
        f"(motivo: {avaliacao.get('reason')})"
    )
    assert avaliacao["reason"] == "estável"


def test_debate_real_continua_reprovado():
    """Contraprova: metade das amostras com múltiplos rostos deve reprovar.

    Sem este teste, "afrouxar o critério" poderia virar "aceitar qualquer
    coisa" — e a Fúria passaria a reenquadrar debates no rosto errado.
    """
    tracker = FaceTracker()
    avaliacao = tracker.assess_segment_tracking(
        _amostras(8, indices_multi=(0, 2, 4, 6), confidence=0.80, t0=100.0, passo=4.0),
        100, 140,
    )

    assert avaliacao["confident"] is False
    assert "múltiplas faces" in avaliacao["reason"]


def test_troca_de_camera_continua_reprovada():
    """O salto de enquadramento é o risco real — deve seguir barrando."""
    tracker = FaceTracker()
    posicoes = _amostras(8)
    posicoes[4]["center_x"] = 0.95   # corte abrupto para o outro lado do quadro

    avaliacao = tracker.assess_segment_tracking(posicoes, 779, 843)

    assert avaliacao["confident"] is False
    assert "câmera" in avaliacao["reason"] or "salto" in avaliacao["reason"]


def test_motivo_da_reprovacao_e_especifico():
    """Antes todo motivo era a mesma frase genérica, inútil para diagnóstico."""
    tracker = FaceTracker()
    avaliacao = tracker.assess_segment_tracking(
        _amostras(8, indices_multi=(0, 2, 4, 6), t0=100.0, passo=4.0), 100, 140
    )

    assert avaliacao["reason"] != "detecção ambígua, múltiplas faces ou troca de câmera", (
        "o motivo precisa dizer QUAL critério falhou, não listar todos"
    )


def test_amostragem_de_layout_cobre_video_longo():
    """`detect_layout` não pode decidir um vídeo de 80 min com 8 frames.

    Medido: `detect_layout` classificou a live como 'fullscreen' (sem rostos)
    enquanto `detect_faces_in_video` encontrou 410 frames com rosto no MESMO
    vídeo. O rótulo 'fullscreen' força 16:9 em todos os cortes.
    """
    import inspect

    from modules import face_tracker

    fonte = inspect.getsource(face_tracker.FaceTracker._detect_layout_mediapipe)

    assert "min(8, max(5, int(duration / 60)))" not in fonte, (
        "regressão: voltou a amostrar só 8 frames para classificar o vídeo"
    )
    assert "min(40, max(12," in fonte, "amostragem mínima de layout ficou baixa demais"

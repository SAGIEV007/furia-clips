"""O tempo de espera da rede tem que caber no que a fonte é.

O diagnóstico que o editor exportou da própria máquina traz a conta inteira,
num vídeo de 139,7 minutos:

    16:00:15  [Gemini] Compactando cópia de análise...
    16:15:41  [Gemini] Enviando a cópia audiovisual compactada...   (15m26s depois)
    16:16:28  [Gemini] Upload concluído...
    16:22:34  [Gemini] Análise multimodal não concluída: Read timed out. (read timeout=180)

Quinze minutos e meio preparando, e três minutos de paciência para o Gemini
analisar duas horas e vinte de material. A chamada estava condenada antes de
sair. Aconteceu duas vezes na mesma sessão — quarenta e cinco minutos de espera
para nenhum resultado, e um editor concluindo, com razão, que "nem ele
funcionou".

O módulo já sabia que a fonte era longa: `_proxy_profile` desce a compressão
para 1 quadro a cada 12 segundos acima de 45 minutos. O que faltava era a outra
metade da mesma informação chegar ao tempo-limite.
"""

from modules.gemini_video import GeminiVideoAnalyzer as G


def test_fonte_curta_espera_pouco_acima_do_piso():
    """O piso é o chão, não o teto de uma fonte curta.

    Cinco minutos ganham 240 s: um minuto a mais que os 180 antigos. A conta é
    piso + proporção, e não faria sentido um vídeo curto esperar *menos* do que
    esperava antes só porque a proporção é pequena.
    """
    espera = G._analysis_timeout(5 * 60)
    assert espera >= G.ANALYSIS_TIMEOUT_MIN_S
    assert espera < 5 * 60, f"{espera}s é espera demais para uma fonte de 5 minutos"


def test_o_video_do_editor_ganha_espera_proporcional():
    """139,7 minutos — o caso real que falhou."""
    espera = G._analysis_timeout(139.7 * 60)
    assert espera > 180, f"continua com a espera fixa que condenou a chamada: {espera}s"
    assert espera >= 15 * 60, f"{espera}s ainda é pouco para 2h20 de material"


def test_a_espera_cresce_com_a_duracao():
    curto = G._analysis_timeout(10 * 60)
    medio = G._analysis_timeout(60 * 60)
    longo = G._analysis_timeout(120 * 60)
    assert curto <= medio <= longo
    assert curto < longo


def test_a_espera_tem_teto():
    """Uma live de oito horas não pode prender o processo a tarde inteira."""
    assert G._analysis_timeout(8 * 60 * 60) == G.ANALYSIS_TIMEOUT_MAX_S


def test_duracao_desconhecida_nao_quebra():
    """`ffprobe` falha e devolve 0; isso não pode virar espera zero nem erro."""
    for valor in (0, None, "", -50):
        assert G._analysis_timeout(valor) == G.ANALYSIS_TIMEOUT_MIN_S

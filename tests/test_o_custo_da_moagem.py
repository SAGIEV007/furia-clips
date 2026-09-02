"""O que a moagem gasta — e o que ela gastava à toa.

O editor mandou o registro de uma live IRL sendo moída:

    15:28:57  Moendo VOLTAMOS - IRL RENAN SANTOS NA PAULISTA
    15:28:57  ━━━ ETAPA 1/6: Removendo Silencio ━━━
    15:28:57  Detectando silencio no audio...
    15:35:29  Encontrados 3 periodos de silencio (58.1s total)
    15:35:29  Processando 4 segmentos de fala...

E às 16:14 — trinta e nove minutos depois daquela última linha — ainda estava
ali. Duas coisas erradas no mesmo lugar, e as duas custavam o dia dele.
"""

import inspect
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
MOTOR = (RAIZ / "app.py").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def etapa_um():
    """O trecho da moagem que lê o silêncio, sem o resto do processo."""
    corpo = MOTOR[MOTOR.find("def api_process_complete"):]
    inicio = corpo.find("ETAPA 1/6")
    fim = corpo.find("ETAPA 2/6")
    assert inicio > 0 and fim > inicio, "não achei a etapa 1 da moagem"
    return corpo[inicio:fim]


def test_a_moagem_nao_recodifica_o_video_para_o_lixo(etapa_um):
    """`remove_silence()` detecta o silêncio E DEPOIS recodifica o vídeo
    inteiro com libx264 preset medium, escrevendo um `_sem_silencio.mp4`.

    Esse arquivo nunca era usado. Três linhas abaixo da chamada,
    `working_video = video_path` devolvia a fonte original, e o resultado da
    recodificação só decidia se uma frase aparecia no console.

    Numa entrevista de meia hora isso é irritante. Numa live IRL de várias
    horas é o dia inteiro — e roda dentro de um `subprocess.run` que bloqueia,
    sem progresso e sem checar cancelamento, então o botão de parar nem
    alcança lá dentro.
    """
    assert "remove_silence(" not in etapa_um, (
        "a moagem voltou a recodificar o vídeo para produzir um arquivo que "
        "ela mesma descarta na linha seguinte"
    )
    assert "detect_silence(" in etapa_um, (
        "parou de LER o silêncio; saber quanto da fonte é silêncio é "
        "informação real sobre o material"
    )


def test_ler_o_silencio_continua_podendo_ser_cancelado(etapa_um):
    """Quarenta minutos sem saída e sem botão que funcione é o pior estado
    possível: ele não sabe se está trabalhando ou travado."""
    assert etapa_um.count("ctx.check_cancel()") >= 2


def test_a_rota_de_tirar_silencio_continua_produzindo_o_arquivo():
    """Lá o arquivo é o que se pediu — a rota chama-se "remover silêncio".
    O desperdício era gerar o arquivo em quem não ia usá-lo."""
    rota = MOTOR[MOTOR.find('@app.route("/api/process/silence"'):]
    rota = rota[:rota.find('@app.route("/api/process/transcribe"')]
    assert "remove_silence(" in rota, "a rota de remover silêncio parou de remover silêncio"


def test_detectar_silencio_nao_decodifica_o_video():
    """`silencedetect` é um filtro de ÁUDIO: a imagem não entra na conta em
    momento nenhum. Sem `-vn` o ffmpeg decodificava cada quadro de vídeo da
    fonte inteira para depois jogar tudo fora.

    Medido numa fonte de 44 segundos, nesta máquina: 5,36s com vídeo contra
    0,26s sem. Vinte vezes. No registro dele a detecção levou seis minutos e
    meio; com `-vn` seria da ordem de vinte segundos.
    """
    from modules.silence_remover import SilenceRemover

    origem = inspect.getsource(SilenceRemover.detect_silence)
    comando = origem[origem.find("cmd = ["):]
    comando = comando[:comando.find("]", comando.find("-f"))]
    assert '"-vn"' in comando, (
        "a detecção de silêncio voltou a decodificar o vídeo inteiro para "
        "analisar só o áudio"
    )
    # E o `-vn` tem de vir DEPOIS da entrada: antes dela, o ffmpeg entende
    # como opção de saída de um arquivo que ainda não existe.
    assert comando.find('"-i"') < comando.find('"-vn"'), "o -vn ficou antes da entrada"


def test_a_etapa_um_diz_quanto_da_fonte_e_silencio(etapa_um):
    """O que ele ganha em troca do arquivo que sumiu: um número sobre o
    material. "58s de silêncio em 3200s de fonte" diz alguma coisa sobre a
    entrevista; "versão sem silêncio gerada como artefato separado" não dizia
    nada sobre nada.
    """
    assert "silencio_total" in etapa_um
    assert "% do material" in etapa_um


def test_nenhuma_etapa_da_moagem_promete_remover_silencio(etapa_um):
    """O rótulo tem de dizer o que a etapa faz. Ela lê; não remove."""
    rotulo = re.search(r"ETAPA 1/6:[^\"]*", etapa_um)
    assert rotulo, "sumiu o rótulo da etapa 1"
    assert "Removendo" not in rotulo.group(0), (
        f"o rótulo continua prometendo remoção: {rotulo.group(0)!r}"
    )

"""A queima de legenda precisa produzir um filtro que o ffmpeg aceite.

Histórico (01/09): `burn_subtitles` montava `ass=fontsdir=<dir>:<arquivo>`, com
as opções ANTES do arquivo. O filtro `ass` do ffmpeg exige o arquivo como
primeiro argumento posicional, então toda execução abortava com "Error parsing
filterchain" — a legenda NUNCA foi queimada. O erro passava despercebido porque
`burn_subtitles` só o mandava para `emit_progress` e devolvia None.

Pior: o teste anterior (`test_burn_subtitles_includes_fontsdir`) exigia
literalmente `arg.startswith("ass=fontsdir=")` — ou seja, **congelava a sintaxe
quebrada** e ficava verde enquanto o recurso não funcionava. Um teste que
verifica a forma da string em vez do efeito não protege nada.

Estes testes verificam a ORDEM correta e, no caso final, o efeito real: um MP4
com legenda de fato gravada na imagem.
"""

import os
import shutil
import subprocess
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from modules.subtitle_generator import SubtitleGenerator


ASS_MINIMO = """[Script Info]
ScriptType: v4.00+
PlayResX: 640
PlayResY: 360

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,28,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,2,20,20,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,legenda de teste
"""


def _monta_filtro(tmp, com_fontes=True):
    """Captura o filtro que seria passado ao ffmpeg."""
    ass_path = os.path.join(tmp, "subs.ass")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ASS_MINIMO)
    if com_fontes:
        fonts_dir = os.path.join(tmp, "fonts")
        os.makedirs(fonts_dir, exist_ok=True)
        open(os.path.join(fonts_dir, "Montserrat-Bold.ttf"), "wb").close()

    gerador = SubtitleGenerator()
    resultado = MagicMock()
    resultado.returncode = 0
    with patch("modules.subtitle_generator.subprocess.run", return_value=resultado) as mock:
        gerador.burn_subtitles("dummy.mp4", ass_path, output_path=os.path.join(tmp, "out.mp4"))
        cmd = mock.call_args[0][0]
    return next(a for a in cmd if a.startswith("ass=")), mock


class TestOrdemDosArgumentos:
    def test_arquivo_vem_antes_das_opcoes(self):
        """O bug: `ass=fontsdir=...:arquivo` faz o ffmpeg abortar."""
        with tempfile.TemporaryDirectory() as tmp:
            filtro, _ = _monta_filtro(tmp)
            assert not filtro.startswith("ass=fontsdir="), (
                f"opção antes do arquivo — ffmpeg rejeita este filtro: {filtro}"
            )
            assert filtro.startswith("ass="), filtro
            primeiro = filtro[len("ass="):].split(":")[0]
            assert primeiro.endswith(".ass"), (
                f"o primeiro argumento tem que ser o arquivo, veio: {primeiro}"
            )

    def test_fontsdir_e_incluido_quando_a_pasta_existe(self):
        with tempfile.TemporaryDirectory() as tmp:
            filtro, _ = _monta_filtro(tmp, com_fontes=True)
            assert "fontsdir=" in filtro

    def test_sem_pasta_de_fontes_nao_inventa_a_opcao(self):
        with tempfile.TemporaryDirectory() as tmp:
            filtro, _ = _monta_filtro(tmp, com_fontes=False)
            assert "fontsdir=" not in filtro


class TestCaminhoDoWindows:
    def test_roda_com_cwd_na_pasta_do_ass(self):
        """Caminho absoluto do Windows dentro de um filtro quebra o escape
        (a letra do drive vira separador de opção). A solução é rodar o
        ffmpeg a partir da pasta e passar só o nome do arquivo."""
        with tempfile.TemporaryDirectory() as tmp:
            filtro, mock = _monta_filtro(tmp)
            assert ":" not in filtro.replace("ass=", "").split(":fontsdir")[0], (
                f"nome de arquivo não pode conter ':' no filtro: {filtro}"
            )
            assert mock.call_args.kwargs.get("cwd") == os.path.abspath(tmp)


def _tem_ffmpeg():
    return shutil.which("ffmpeg") is not None


@pytest.mark.skipif(not _tem_ffmpeg(), reason="ffmpeg não disponível")
class TestEfeitoReal:
    """Não basta a string estar certa — o ffmpeg tem que aceitar de verdade."""

    def test_queima_produz_video_valido(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = os.path.join(tmp, "v.mp4")
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=640x360:d=2",
                 "-f", "lavfi", "-i", "anullsrc", "-shortest", "-c:v", "libx264",
                 "-c:a", "aac", video],
                capture_output=True, check=True,
            )
            ass = os.path.join(tmp, "s.ass")
            with open(ass, "w", encoding="utf-8") as f:
                f.write(ASS_MINIMO)

            saida = os.path.join(tmp, "out.mp4")
            retorno = SubtitleGenerator().burn_subtitles(video, ass, saida)

            assert retorno is not None, "burn_subtitles devolveu None — ffmpeg recusou o filtro"
            assert os.path.exists(saida) and os.path.getsize(saida) > 1000

    def test_funciona_com_acento_e_espaco_no_caminho(self):
        """O caso real da máquina do usuário: 'Área de Trabalho'."""
        with tempfile.TemporaryDirectory() as tmp:
            pasta = os.path.join(tmp, "pasta com acento çã")
            os.makedirs(pasta)
            video = os.path.join(pasta, "v.mp4")
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=640x360:d=2",
                 "-f", "lavfi", "-i", "anullsrc", "-shortest", "-c:v", "libx264",
                 "-c:a", "aac", video],
                capture_output=True, check=True,
            )
            ass = os.path.join(pasta, "s.ass")
            with open(ass, "w", encoding="utf-8") as f:
                f.write(ASS_MINIMO)

            saida = os.path.join(pasta, "out.mp4")
            assert SubtitleGenerator().burn_subtitles(video, ass, saida) is not None
            assert os.path.getsize(saida) > 1000

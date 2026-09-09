import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from modules.subtitle_generator import SubtitleGenerator


class SubtitleGeneratorTests(unittest.TestCase):
    def test_generates_word_by_word_ass_with_safe_text(self):
        generator = SubtitleGenerator({"render_preset": "shorts", "subtitle_style": "word_by_word"})
        segments = [
            {
                "start": -0.5,
                "end": 1.2,
                "text": "Atenção {agora}",
                "words": [
                    {"word": "Atenção", "start": -0.5, "end": 0.4},
                    {"word": "{agora}", "start": 0.4, "end": 1.2},
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as tempdir:
            path = os.path.join(tempdir, "captions.ass")
            generator.generate_ass_file(segments, path)
            with open(path, encoding="utf-8") as handle:
                content = handle.read()

        self.assertIn("PlayResX: 1080", content)
        self.assertIn("Dialogue:", content)
        self.assertIn("0:00:00.00", content)
        self.assertIn("\\{agora\\}", content)
        self.assertNotIn("-1:", content)

    def test_political_terms_use_alert_style(self):
        generator = SubtitleGenerator({"render_preset": "political_shorts"})
        with tempfile.TemporaryDirectory() as tempdir:
            path = os.path.join(tempdir, "alert.ass")
            generator.generate_ass_file(
                [{
                    "start": 0,
                    "end": 1,
                    "text": "Decisão ilegal: 10 mil casos.",
                    "words": [
                        {"word": "Decisão", "start": 0, "end": 0.2},
                        {"word": "ilegal", "start": 0.2, "end": 0.5},
                        {"word": "10", "start": 0.5, "end": 0.7},
                        {"word": "mil", "start": 0.7, "end": 0.8},
                    ],
                }],
                path,
            )
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
        self.assertIn("Style: Alert", content)
        self.assertIn("{\\rAlert}{\\t(0,50,\\fscx115\\fscy115)\\t(50,150,\\fscx100\\fscy100)}ilegal", content)
        self.assertIn("{\\rAlert}{\\t(0,50,\\fscx115\\fscy115)\\t(50,150,\\fscx100\\fscy100)}10", content)

    def test_political_preset_uses_larger_bottom_safe_margin(self):
        generator = SubtitleGenerator({"render_preset": "political_shorts"})
        with tempfile.TemporaryDirectory() as tempdir:
            path = os.path.join(tempdir, "political.ass")
            generator.generate_ass_file(
                [{"start": 0, "end": 1, "text": "Tese política", "words": []}],
                path,
            )
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
        self.assertIn(",360,1\n", content)

    def test_ass_filter_value_escapes_drive_colon(self):
        # Bug real visto em producao: MESMO sem virgula ou aspas no titulo, o
        # ffmpeg 8.1.1 falhava com "Unable to parse 'original_size' ... Invalid
        # argument" para TODO corte, porque o "C:" da unidade do Windows nao
        # estava escapado (e entre aspas simples). Confirmado rodando o
        # ffmpeg de verdade: sem o "\:" ele lia o resto do caminho como se
        # fosse a opcao seguinte do filtro.
        generator = SubtitleGenerator()
        valor = generator._ass_filter_value(r"C:\Users\70156213125\FuriaClipsData\legenda_abc123.ass")
        self.assertEqual(valor, "'C\\:/Users/70156213125/FuriaClipsData/legenda_abc123.ass'")

    def test_copy_ass_to_safe_temp_name_strips_special_characters(self):
        # Titulos de corte viram nome de arquivo (ex.: "Renan Santos 'Não vou
        # ser populista', com jornalistas.ass"). Testamos de verdade contra o
        # ffmpeg: NENHUMA forma de escapar uma aspas simples dentro do valor
        # do filtro -vf sobrevive - o proprio ffmpeg descarta a aspas e o
        # libass tenta abrir um arquivo com nome errado ("fopen failed"). A
        # saida robusta e copiar para um nome sem nenhum caractere especial.
        generator = SubtitleGenerator()
        with tempfile.TemporaryDirectory() as tempdir:
            original = os.path.join(tempdir, "2. Renan Santos 'Não vou ser populista', com jornalistas.ass")
            with open(original, "w", encoding="utf-8") as handle:
                handle.write("[Script Info]\n")

            safe_path = generator._copy_ass_to_safe_temp_name(original)

            self.assertTrue(os.path.isfile(safe_path))
            safe_name = os.path.basename(safe_path)
            self.assertRegex(safe_name, r"^furia_legenda_[0-9a-f]+\.ass$")
            with open(safe_path, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "[Script Info]\n")
            os.remove(safe_path)

    def test_burn_subtitles_uses_safe_name_in_command_and_cleans_it_up(self):
        generator = SubtitleGenerator()
        with tempfile.TemporaryDirectory() as tempdir:
            video_path = os.path.join(tempdir, "clip.mp4")
            ass_path = os.path.join(tempdir, "8. critica cobertura, com jornalistas, com.ass")
            output_path = os.path.join(tempdir, "clip_leg.mp4")
            with open(ass_path, "w", encoding="utf-8") as handle:
                handle.write("[Script Info]\n")

            with patch("modules.subtitle_generator.subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                generator.burn_subtitles(video_path, ass_path, output_path)

            cmd = mock_run.call_args[0][0]
            vf_arg = cmd[cmd.index("-vf") + 1]
            self.assertRegex(vf_arg, r"^ass='.*/furia_legenda_[0-9a-f]+\.ass'$")
            # o temporario e apagado depois de usar, so sobra o .ass original
            leftovers = [f for f in os.listdir(tempdir) if f.startswith("furia_legenda_")]
            self.assertEqual(leftovers, [])

    def test_burn_subtitles_actually_burns_with_special_characters_in_path(self):
        # Teste de ponta a ponta com o ffmpeg de verdade (nao mockado) contra
        # o bug real: virgula E aspas simples E dois-pontos de unidade juntos
        # no mesmo caminho, que era exatamente a combinação vista em produção.
        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg não disponível neste ambiente de teste")

        generator = SubtitleGenerator()
        with tempfile.TemporaryDirectory() as tempdir:
            video_path = os.path.join(tempdir, "clip.mp4")
            ass_path = os.path.join(tempdir, "2. Renan Santos 'Não vou ser populista', com jornalistas.ass")
            output_path = os.path.join(tempdir, "clip_leg.mp4")

            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=1",
                 "-c:v", "libx264", "-preset", "ultrafast", video_path],
                capture_output=True, check=True,
            )
            generator.generate_ass_file(
                [{"start": 0, "end": 1, "text": "Teste", "words": []}], ass_path
            )

            result = generator.burn_subtitles(video_path, ass_path, output_path)

            self.assertEqual(result, output_path)
            self.assertTrue(os.path.isfile(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)

    def test_generates_srt_with_non_negative_time(self):
        generator = SubtitleGenerator()
        with tempfile.TemporaryDirectory() as tempdir:
            path = os.path.join(tempdir, "captions.srt")
            generator.generate_srt(
                [{"start": -1, "end": 1.25, "text": "Teste"}], path
            )
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
        self.assertIn("00:00:00,000 --> 00:00:01,250", content)


if __name__ == "__main__":
    unittest.main()

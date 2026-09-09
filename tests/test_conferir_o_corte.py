"""O corte mudo passava na conferência e era entregue.

A BRECHA
--------
`validate_media` confere o arquivo pelos METADADOS: duração bate, resolução
bate, existe uma faixa de vídeo, existe uma faixa de áudio.

Existir uma faixa de áudio não é o mesmo que ter som. Um corte inteiramente
mudo tem faixa de áudio, passa, e é entregue ao editor. Uma tela preta — o
trecho onde a transmissão caiu — tem faixa de vídeo.

O estudo que ele mandou lista exatamente isto na etapa de QA antes de entregar:
"ausência de frames pretos, congelamentos e silêncio inesperado".

O QUE ESTA CONFERÊNCIA NÃO FAZ
------------------------------
Não reprova nada. Um manifesto com cinco segundos de silêncio dramático é bom,
e quem decide é ele. E nunca levanta: perder um corte bom por causa da
conferência é pior do que entregar um corte para ele olhar.
"""

import subprocess
import unittest
from unittest.mock import patch

from modules.conferir_o_corte import conferir

# Como o ffmpeg escreve, com as duas famílias de linha misturadas na saída de
# erro, que é onde ele imprime tudo.
SAIDA_LIMPA = "frame= 1500 fps=... \nvideo:0kB audio:0kB\n"
SAIDA_COM_PRETO = (
    "[blackdetect @ 0x1] black_start:12.5 black_end:18.2 black_duration:5.7\n"
    "[blackdetect @ 0x1] black_start:40.0 black_end:42.0 black_duration:2.0\n"
)
SAIDA_COM_SILENCIO = (
    "[silencedetect @ 0x2] silence_start: 5.12\n"
    "[silencedetect @ 0x2] silence_end: 11.40 | silence_duration: 6.28\n"
)


def _ffmpeg_que_responde(saida, codigo=0):
    return patch("modules.conferir_o_corte.subprocess.run",
                 return_value=subprocess.CompletedProcess([], codigo, "", saida))


class OCorteLimpoPassaSemAviso(unittest.TestCase):
    def test_nenhum_aviso_quando_nao_ha_nada(self):
        with _ffmpeg_que_responde(SAIDA_LIMPA):
            resultado = conferir("corte.mp4", duracao_s=60.0)

        self.assertTrue(resultado["conferido"])
        self.assertEqual(resultado["avisos"], [])
        self.assertEqual(resultado["preto_s"], 0.0)
        self.assertEqual(resultado["silencio_s"], 0.0)


class OQueEleVeriaNaTela(unittest.TestCase):
    def test_tela_preta_vira_aviso_com_o_tamanho_do_maior_trecho(self):
        with _ffmpeg_que_responde(SAIDA_COM_PRETO):
            resultado = conferir("corte.mp4", duracao_s=60.0)

        self.assertEqual(resultado["preto_s"], 7.7)
        self.assertIn("2 trecho(s) de tela preta", resultado["avisos"][0])
        self.assertIn("5.7s", resultado["avisos"][0])

    def test_silencio_vira_aviso(self):
        with _ffmpeg_que_responde(SAIDA_COM_SILENCIO):
            resultado = conferir("corte.mp4", duracao_s=60.0)

        self.assertEqual(resultado["silencio_s"], 6.28)
        self.assertIn("sem som", resultado["avisos"][0])

    def test_os_dois_juntos_viram_dois_avisos(self):
        with _ffmpeg_que_responde(SAIDA_COM_PRETO + SAIDA_COM_SILENCIO):
            resultado = conferir("corte.mp4", duracao_s=60.0)

        self.assertEqual(len(resultado["avisos"]), 2)


class OCasoGraveTemQueGritar(unittest.TestCase):
    """Corte inteiro mudo não é 'um aviso entre outros': é um corte que não existe."""

    def test_corte_mudo_do_comeco_ao_fim(self):
        saida = ("[silencedetect @ 0x2] silence_start: 0.0\n"
                 "[silencedetect @ 0x2] silence_end: 40.0\n")
        with _ffmpeg_que_responde(saida):
            resultado = conferir("corte.mp4", duracao_s=40.0)

        self.assertIn("ESTE CORTE ESTÁ MUDO DO COMEÇO AO FIM", resultado["avisos"])

    def test_corte_preto_do_comeco_ao_fim(self):
        saida = "[blackdetect @ 0x1] black_start:0.0 black_end:40.0 black_duration:40.0\n"
        with _ffmpeg_que_responde(saida):
            resultado = conferir("corte.mp4", duracao_s=40.0)

        self.assertIn("ESTE CORTE ESTÁ PRETO DO COMEÇO AO FIM", resultado["avisos"])

    def test_pausa_dramatica_no_meio_nao_e_o_caso_grave(self):
        with _ffmpeg_que_responde(SAIDA_COM_SILENCIO):
            resultado = conferir("corte.mp4", duracao_s=60.0)

        self.assertTrue(all("COMEÇO AO FIM" not in aviso for aviso in resultado["avisos"]))

    def test_sem_a_duracao_o_caso_grave_nao_e_adivinhado(self):
        saida = ("[silencedetect @ 0x2] silence_start: 0.0\n"
                 "[silencedetect @ 0x2] silence_end: 40.0\n")
        with _ffmpeg_que_responde(saida):
            resultado = conferir("corte.mp4")

        self.assertTrue(all("COMEÇO AO FIM" not in aviso for aviso in resultado["avisos"]))


class ConferirNuncaDerrubaAEntrega(unittest.TestCase):
    def test_sem_ffmpeg_devolve_nao_conferido_em_vez_de_levantar(self):
        with patch("modules.conferir_o_corte.subprocess.run",
                   side_effect=FileNotFoundError("ffmpeg")):
            resultado = conferir("corte.mp4", duracao_s=60.0)

        self.assertFalse(resultado["conferido"])
        self.assertEqual(resultado["avisos"], [])

    def test_conferencia_que_demora_demais_desiste_em_silencio(self):
        with patch("modules.conferir_o_corte.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("ffmpeg", 120)):
            self.assertFalse(conferir("corte.mp4")["conferido"])

    def test_caminho_vazio_nem_chama_o_ffmpeg(self):
        with patch("modules.conferir_o_corte.subprocess.run") as chamou:
            conferir("")
        chamou.assert_not_called()


class ALigacaoComAMoagem(unittest.TestCase):
    """Sem isto o módulo existe e ninguém o chama — que foi o defeito do
    caderninho do Acervo e o da marcação de palavra."""

    def test_o_cortador_confere_e_carrega_o_resultado(self):
        from pathlib import Path

        fonte = (Path(__file__).resolve().parents[1] / "modules" / "video_cutter.py")
        texto = fonte.read_text(encoding="utf-8")
        self.assertIn("from .conferir_o_corte import conferir", texto)
        self.assertIn('"conferencia": conferencia,', texto,
                      "o resultado precisa viajar com o corte, não morrer na função")


if __name__ == "__main__":
    unittest.main()

"""Achar a hora de cada palavra sem escutar o vídeo inteiro de novo.

O PEDIDO DELE, CORTE A CORTE
----------------------------
    "o corte 18 deveria começar em 0:25, em 'candidato'"

Para encostar a borda em "candidato" o programa precisa saber em que segundo
essa palavra começa. Quem escuta o áudio sabe; um texto colado à mão não sabe,
e não tem como saber — a informação nunca existiu ali.

POR QUE ISSO IMPORTAVA TANTO
----------------------------
No banco dele, das 26 transcrições guardadas, 21 são texto colado:

    Ceará (08/09) .......... texto colado
    Flow News (05/09) ...... texto colado
    Paulista (02/09) ....... o programa escutou

Ou seja: no material que ele MAIS moe, a borda nunca teve como ser acertada.

A CONTA
-------
Escutar uma fonte de 1h30 inteira custa dezenas de minutos e joga fora quase
tudo — só as bordas interessam. Escutando apenas as janelas que já viraram
corte são vinte trechos de um a dois minutos.
"""

import unittest
from unittest.mock import patch

from modules.clip_selector import ClipSelector
from modules.palavras_dos_trechos import _juntar_janelas, palavras_das_janelas


class QuaisTrechosEscutar(unittest.TestCase):
    def test_a_janela_ganha_folga_dos_dois_lados(self):
        """A palavra que abre o corte começa um pouco antes do segundo pedido."""
        self.assertEqual(_juntar_janelas([(100.0, 160.0)], folga=3.0), [(97.0, 163.0)])

    def test_a_folga_nao_puxa_para_antes_do_comeco_do_video(self):
        self.assertEqual(_juntar_janelas([(1.0, 40.0)], folga=3.0), [(0.0, 43.0)])

    def test_cortes_vizinhos_viram_uma_escuta_so(self):
        """Escutar duas vezes o mesmo áudio é tempo dele jogado fora."""
        juntas = _juntar_janelas([(10.0, 70.0), (72.0, 130.0)], folga=3.0)
        self.assertEqual(juntas, [(7.0, 133.0)])

    def test_cortes_distantes_continuam_duas_escutas(self):
        juntas = _juntar_janelas([(10.0, 70.0), (600.0, 660.0)], folga=3.0)
        self.assertEqual(len(juntas), 2)

    def test_janela_torta_e_ignorada_sem_quebrar(self):
        juntas = _juntar_janelas([(50.0, 10.0), ("x", 3), None, (10.0, 70.0)])
        self.assertEqual(len(juntas), 1)


class EscutarDeVerdade(unittest.TestCase):
    def test_as_horas_voltam_em_segundos_do_video_inteiro(self):
        """O reconhecedor conta do zero DENTRO do pedaço.

        Sem somar o deslocamento da janela, uma palavra dos 20 minutos voltaria
        marcada aos 3 segundos e o corte pularia para o começo do vídeo.
        """
        class OuvinteFalso:
            def transcribe(self, caminho):
                return {"segments": [{"words": [
                    {"word": "candidato", "start": 3.0, "end": 3.6},
                    {"word": "que", "start": 3.6, "end": 3.8},
                ]}]}

        with patch("modules.palavras_dos_trechos.os.path.isfile", return_value=True), \
             patch("modules.palavras_dos_trechos._extrair_audio", return_value="x.wav"):
            palavras = palavras_das_janelas("v.mp4", [(1200.0, 1260.0)], OuvinteFalso())

        self.assertEqual(len(palavras), 2)
        # janela abre em 1200 - 3 de folga = 1197; a palavra cai 3 s depois
        self.assertAlmostEqual(palavras[0]["start"], 1200.0, places=3)
        self.assertEqual(palavras[0]["word"], "candidato")

    def test_um_trecho_que_falha_nao_derruba_os_outros(self):
        """Borda melhor é ganho; perder a moagem por causa dela, não."""
        class OuvinteRabugento:
            def __init__(self):
                self.vezes = 0

            def transcribe(self, caminho):
                self.vezes += 1
                if self.vezes == 1:
                    raise RuntimeError("áudio ilegível")
                return {"segments": [{"words": [
                    {"word": "ok", "start": 1.0, "end": 1.4}]}]}

        with patch("modules.palavras_dos_trechos.os.path.isfile", return_value=True), \
             patch("modules.palavras_dos_trechos._extrair_audio", return_value="x.wav"):
            palavras = palavras_das_janelas(
                "v.mp4", [(10.0, 70.0), (600.0, 660.0)], OuvinteRabugento())

        self.assertEqual(len(palavras), 1, "o segundo trecho ainda rendeu")

    def test_sem_video_no_disco_devolve_vazio(self):
        self.assertEqual(palavras_das_janelas("nao-existe.mp4", [(1.0, 9.0)], None), [])

    def test_sem_corte_nenhum_nao_escuta_nada(self):
        with patch("modules.palavras_dos_trechos.os.path.isfile", return_value=True):
            self.assertEqual(palavras_das_janelas("v.mp4", [], None), [])


class OSeletorUsaIssoQuandoOTextoEColado(unittest.TestCase):
    def _seletor(self):
        seletor = ClipSelector.__new__(ClipSelector)
        seletor.min_duration = 10.0
        seletor.max_duration = 180.0
        seletor.MIN_WORDS_FOR_BOUNDARY_REFINEMENT = 3
        seletor.MIN_WORD_BOUNDARY_COVERAGE = 0.5
        seletor.MAX_WORD_BOUNDARY_SHIFT_S = 3.0
        seletor._candidate_diagnostics = {}
        seletor._caminho_da_midia = "v.mp4"
        seletor._escutar_bordas_ligado = True
        seletor._modelo_para_bordas = "small"
        return seletor

    def test_texto_colado_faz_o_programa_escutar_as_bordas(self):
        seletor = self._seletor()
        palavras = [{"word": "candidato", "start": 25.0, "end": 25.6}]
        instante = 25.6
        for numero in range(70):
            palavras.append({"word": f"p{numero}", "start": instante, "end": instante + 0.5})
            instante += 0.5

        # Transcrição sem "words" — exatamente o texto colado dele.
        segmentos = [{"start": 24.0, "end": 62.0, "text": "..."}]
        cortes = [{"start": 24.3, "end": 60.8,
                   "text": " ".join(p["word"] for p in palavras)}]

        with patch.object(ClipSelector, "_escutar_so_as_bordas", return_value=palavras):
            resultado = seletor._refine_boundaries_with_words(cortes, segmentos)

        self.assertEqual(resultado[0]["start"], 25.0,
                         "o corte passa a começar exatamente em 'candidato'")
        self.assertTrue(
            seletor._candidate_diagnostics["word_boundary_segments_available"])

    def test_quando_a_transcricao_ja_tem_as_horas_nao_escuta_de_novo(self):
        """Escutar de novo o que já se sabe é tempo dele jogado fora."""
        seletor = self._seletor()
        segmentos = [{"start": 0.0, "end": 40.0, "words": [
            {"word": "ja", "start": 1.0, "end": 1.5}]}]

        with patch.object(ClipSelector, "_escutar_so_as_bordas") as escuta:
            seletor._refine_boundaries_with_words([{"start": 1.0, "end": 30.0, "text": "ja"}],
                                                  segmentos)
        escuta.assert_not_called()

    def test_sem_video_a_moagem_segue_com_as_bordas_que_tem(self):
        seletor = self._seletor()
        seletor._caminho_da_midia = ""

        self.assertEqual(seletor._escutar_so_as_bordas([{"start": 1.0, "end": 9.0}]), [])

    def test_desligar_a_escuta_e_respeitado(self):
        seletor = self._seletor()
        seletor._escutar_bordas_ligado = False

        self.assertEqual(seletor._escutar_so_as_bordas([{"start": 1.0, "end": 9.0}]), [])

    def test_erro_ao_escutar_nunca_derruba_a_moagem(self):
        seletor = self._seletor()
        avisos = []

        with patch("modules.transcriber.Transcriber", side_effect=RuntimeError("sem modelo")):
            resultado = seletor._escutar_so_as_bordas(
                [{"start": 1.0, "end": 9.0}],
                lambda texto, nivel=None: avisos.append(texto),
            )

        self.assertEqual(resultado, [])


if __name__ == "__main__":
    unittest.main()

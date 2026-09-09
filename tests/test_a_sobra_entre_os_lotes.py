"""Uma fala que atravessa a emenda entre dois lotes não era vista por ninguém.

DE ONDE VEIO
------------
O editor mandou um programa de referência (Anil-matcha/AI-Youtube-Shorts-
Generator) perguntando se havia algo aproveitável. Do programa em si, não —
ele manda a transcrição inteira para um serviço de fora, o que está fora de
questão para material do Renan. Mas ele fatia vídeo longo com 60 segundos de
sobra entre um pedaço e o outro, e isso o Furia não fazia.

O DEFEITO
---------
A transcrição não cabe num pedido só, então ela vai em lotes. Os lotes eram
encostados:

    lote 1: blocos 0..7
    lote 2:               8..15
    lote 3:                      16..23

Uma fala que começa no bloco 7 e fecha no 8 não aparece INTEIRA em lote
nenhum. O primeiro lote vê só a abertura e descarta por não fechar o
raciocínio; o segundo vê só o fecho e descarta por começar no meio. Numa
fonte de 1h30 são dezenas dessas emendas.

O PREÇO
-------
Dois blocos de sobra dão cerca de um terço a mais de requisições. Em troca,
toda fala aparece inteira em pelo menos um lote.

E a sobra tem um efeito colateral que PRECISA de trava: o mesmo trecho passa
a ser oferecido por dois lotes. Sem juntar de volta, a sobra viraria
exatamente a reclamação dele — "tive a impressão de serem cortes do mesmo
trecho".
"""

import unittest

from modules.clip_selector import ClipSelector


class ALaminaCaiEntreOsLotes(unittest.TestCase):
    def _blocos(self, quantos):
        return [{"i": n, "start": n * 10.0, "end": n * 10.0 + 10.0} for n in range(quantos)]

    def test_toda_fala_de_dois_blocos_aparece_inteira_em_algum_lote(self):
        """A prova do que o defeito custava: par vizinho sem lote que o contenha."""
        blocos = self._blocos(24)
        lotes = [lote for _, lote in ClipSelector._lotes_com_sobra(blocos, 8, 2)]

        for primeiro in range(len(blocos) - 1):
            par = {primeiro, primeiro + 1}
            coube = any(par <= {b["i"] for b in lote} for lote in lotes)
            self.assertTrue(
                coube,
                f"a fala que vai do bloco {primeiro} ao {primeiro + 1} não cabe "
                f"inteira em lote nenhum",
            )

    def test_sem_sobra_a_fala_da_emenda_se_perde(self):
        """O comportamento antigo, guardado para não voltar sem ninguém ver."""
        blocos = self._blocos(24)
        encostados = [lote for _, lote in ClipSelector._lotes_com_sobra(blocos, 8, 0)]

        par = {7, 8}
        coube = any(par <= {b["i"] for b in lote} for lote in encostados)
        self.assertFalse(coube, "é exatamente o que a sobra veio consertar")

    def test_nenhum_bloco_fica_de_fora(self):
        blocos = self._blocos(23)
        lotes = ClipSelector._lotes_com_sobra(blocos, 8, 2)
        vistos = set()
        for _, lote in lotes:
            vistos.update(b["i"] for b in lote)
        self.assertEqual(vistos, set(range(23)))

    def test_a_posicao_do_lote_vem_junto_e_esta_certa(self):
        """A posição vai no prompt; procurá-la depois pelo conteúdo erraria."""
        blocos = self._blocos(24)
        for inicio, lote in ClipSelector._lotes_com_sobra(blocos, 8, 2):
            self.assertEqual(lote[0]["i"], inicio)

    def test_sobra_maior_que_o_lote_nao_trava_o_programa(self):
        """Passo zero seria laço infinito — e travar a moagem dele é pior que
        qualquer corte perdido."""
        blocos = self._blocos(10)
        lotes = ClipSelector._lotes_com_sobra(blocos, 4, 99)
        self.assertGreater(len(lotes), 0)
        self.assertLess(len(lotes), 50)
        vistos = set()
        for _, lote in lotes:
            vistos.update(b["i"] for b in lote)
        self.assertEqual(vistos, set(range(10)))

    def test_transcricao_curta_cabe_num_lote_so(self):
        blocos = self._blocos(5)
        lotes = ClipSelector._lotes_com_sobra(blocos, 8, 2)
        self.assertEqual(len(lotes), 1)

    def test_transcricao_vazia_nao_quebra(self):
        self.assertEqual(ClipSelector._lotes_com_sobra([], 8, 2), [])


class ASobraNaoPodeVirarCorteRepetido(unittest.TestCase):
    def test_o_mesmo_trecho_vindo_de_dois_lotes_vira_um(self):
        selecoes = [
            {"start": 10.0, "end": 70.0, "viral_score": 72},
            {"start": 10.0, "end": 70.0, "viral_score": 80},   # o mesmo, outro lote
            {"start": 200.0, "end": 260.0, "viral_score": 65},
        ]

        resultado = ClipSelector._sem_repetir_o_mesmo_trecho(selecoes)

        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[0]["viral_score"], 80, "fica o de maior nota")

    def test_trechos_diferentes_continuam_dois(self):
        selecoes = [
            {"start": 10.0, "end": 70.0, "viral_score": 72},
            {"start": 12.0, "end": 75.0, "viral_score": 71},
        ]
        self.assertEqual(len(ClipSelector._sem_repetir_o_mesmo_trecho(selecoes)), 2)

    def test_candidato_torto_nao_derruba_a_moagem(self):
        selecoes = [
            {"start": "nada", "end": 70.0},
            None,
            {"start": 10.0, "end": 70.0, "viral_score": 50},
        ]
        resultado = ClipSelector._sem_repetir_o_mesmo_trecho(selecoes)
        self.assertEqual(len(resultado), 1)


if __name__ == "__main__":
    unittest.main()

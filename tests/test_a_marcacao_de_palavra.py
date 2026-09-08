"""O passo que encosta o corte na borda da palavra nunca rodou na máquina dele.

O QUE ELE PEDIU, CORTE A CORTE
------------------------------
    "o corte 18 deveria começar em 0:25, em 'candidato'"

Para começar EM "candidato" o programa precisa saber a que segundo essa
palavra começa. Isso se chama marcação de palavra, e o Furia tem o passo que
usa isso desde sempre — `_refine_boundaries_with_words`.

O QUE OS NÚMEROS DELE MOSTRAM
-----------------------------
Nos três últimos relatórios de moagem que ele mandou (Paulista 02/09,
Flow News 05/09, Ceará 08/09), os três dizem a mesma coisa:

    word_boundary_segments_available: False
    word_boundary_refined_count: 0

E no banco dele, 26 transcrições guardadas, NENHUMA com marcação de palavra —
nem as 4 feitas pelo Whisper local.

POR QUE
-------
Em agosto o padrão nasceu desligado e foi gravado no banco. Depois o padrão
virou ligado, mas valor gravado ganha do padrão. E nunca existiu tela para
mudar isso — ele não tinha como ter escolhido, e não tinha como desfazer.

    whisper_word_timestamps = false   (no banco dele, até hoje)
"""

import json
import sqlite3
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class AMarcacaoDePalavraVoltaSozinha(unittest.TestCase):
    def setUp(self):
        self.raiz = Path(tempfile.mkdtemp(prefix="palavra-"))
        self.addCleanup(shutil.rmtree, self.raiz, ignore_errors=True)
        self.banco = self.raiz / "banco.sqlite3"

    def _valor(self, chave):
        conexao = sqlite3.connect(self.banco)
        linha = conexao.execute(
            "SELECT value FROM settings WHERE key = ?", (chave,)).fetchone()
        conexao.close()
        return None if linha is None else json.loads(linha[0])

    def _gravar(self, chave, valor):
        conexao = sqlite3.connect(self.banco)
        conexao.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                        (chave, json.dumps(valor)))
        conexao.commit()
        conexao.close()

    def _abrir(self):
        import database

        with patch.object(database, "DB_PATH", str(self.banco)), \
             patch("config.DB_PATH", str(self.banco)):
            database.init_db()

    def test_o_banco_antigo_dele_volta_ligado(self):
        """É o caso exato do banco que ele mandou."""
        self._abrir()
        self._gravar("whisper_word_timestamps", False)
        self._gravar("marcacao_de_palavra_religada", None)
        conexao = sqlite3.connect(self.banco)
        conexao.execute("DELETE FROM settings WHERE key = 'marcacao_de_palavra_religada'")
        conexao.commit()
        conexao.close()

        self._abrir()

        self.assertTrue(self._valor("whisper_word_timestamps"),
                        "sem isso o corte nunca encosta na borda da palavra")

    def test_banco_novo_ja_nasce_ligado(self):
        self._abrir()
        self.assertTrue(self._valor("whisper_word_timestamps"))

    def test_so_conserta_uma_vez(self):
        """Se um dia houver tela para desligar, a escolha dele fica de pé."""
        self._abrir()
        self._gravar("whisper_word_timestamps", False)

        self._abrir()

        self.assertFalse(self._valor("whisper_word_timestamps"),
                         "o conserto já foi feito; a partir daqui quem manda é ele")

    def test_o_padrao_do_programa_esta_ligado(self):
        from config import DEFAULT_SETTINGS

        self.assertTrue(DEFAULT_SETTINGS["whisper_word_timestamps"])


class OPassoUsaAMarcacaoQuandoEla_Existe(unittest.TestCase):
    """Ligar a marcação só serve se o passo de fato mexer na borda."""

    def test_com_marcacao_a_borda_anda_para_o_comeco_da_palavra(self):
        from modules.clip_selector import ClipSelector

        seletor = ClipSelector.__new__(ClipSelector)
        seletor.min_duration = 10.0
        seletor.max_duration = 180.0
        seletor.MIN_WORDS_FOR_BOUNDARY_REFINEMENT = 3
        seletor.MIN_WORD_BOUNDARY_COVERAGE = 0.5
        seletor.MAX_WORD_BOUNDARY_SHIFT_S = 2.0
        seletor._candidate_diagnostics = {}

        palavras = [{"word": "candidato", "start": 25.0, "end": 25.6}]
        # Uma fala de trinta e cinco segundos, palavra a palavra.
        instante = 25.6
        for numero in range(70):
            palavras.append({"word": f"p{numero}", "start": instante,
                             "end": instante + 0.5})
            instante += 0.5

        segmentos = [{"start": 24.0, "end": 62.0, "words": palavras}]
        cortes = [{"start": 24.3, "end": 60.8,
                   "text": " ".join(item["word"] for item in palavras)}]

        resultado = seletor._refine_boundaries_with_words(cortes, segmentos)

        self.assertEqual(resultado[0]["start"], 25.0,
                         "o corte passa a começar exatamente em 'candidato'")
        self.assertEqual(
            seletor._candidate_diagnostics["word_boundary_segments_available"], True)
        self.assertEqual(
            seletor._candidate_diagnostics["word_boundary_refined_count"], 1)


if __name__ == "__main__":
    unittest.main()

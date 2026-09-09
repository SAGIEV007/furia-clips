"""Antes de cortar, dizer em voz alta se o Acervo entrou ou não.

O PEDIDO DELE
-------------
    "quero uma forma de me certificar de que ele está sendo usado e fazendo
     diferença de fato"

E a razão do pedido, nas palavras dele: o CHUB estava sendo usado "apenas como
enfeite de mesa". Ele estava certo — no ato de 7 de setembro o CHUB tinha 21
blocos revisados e nenhuma das 7 fronteiras do Furia bateu com nenhuma delas,
porque o Furia nunca chegou a perguntar.

O QUE ESTE ARQUIVO PROTEGE
--------------------------
Três ligações que existiam pela metade:

1. Um dos dois caminhos de moagem NUNCA consultava o Acervo. Duas portas para
   a mesma sala, e uma delas cortava sempre às cegas.
2. O aviso mandava o editor digitar `chub.bat --vincular` num terminal. A regra
   dele é antiga: se ele precisa fazer alguma coisa, existe um botão.
3. O estado do Acervo só aparecia numa linha de console, que rola e some. Agora
   vai para o arquivo de diagnóstico, que é o que ele me manda.
"""

import ast
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _fonte(nome):
    return (RAIZ / nome).read_text(encoding="utf-8")


class OsDoisCaminhosDeMoagemConsultamOAcervo(unittest.TestCase):
    """O defeito era assimetria: um caminho perguntava, o outro não."""

    def test_todo_caminho_que_moe_pergunta_ao_acervo(self):
        app = _fonte("app.py")
        self.assertEqual(
            app.count("_settings_with_acervo(get_all_settings()"), 3,
            "os três caminhos que preparam uma moagem precisam consultar o Acervo",
        )

    def test_todo_caminho_que_moe_anuncia_o_que_achou(self):
        app = _fonte("app.py")
        self.assertEqual(
            app.count('settings["acervo"] = _announce_acervo_source(settings'), 2,
            "consultar sem anunciar deixa o editor no escuro de novo",
        )


class OAvisoFalaDeBotaoENaoDeComando(unittest.TestCase):
    def _corpo_do_aviso(self):
        app = _fonte("app.py")
        arvore = ast.parse(app)
        for no in ast.walk(arvore):
            if isinstance(no, ast.FunctionDef) and no.name == "_announce_acervo_source":
                return ast.get_source_segment(app, no)
        self.fail("_announce_acervo_source sumiu")

    def test_nao_manda_ninguem_digitar_comando(self):
        """Ele não usa terminal. Mandar digitar é o mesmo que não avisar."""
        corpo = self._corpo_do_aviso()
        for comando in ["chub.bat --vincular", "chub.bat {youtube_id}", "--espelho"]:
            self.assertNotIn(comando, corpo, f"o aviso ainda manda digitar '{comando}'")

    def test_aponta_para_o_botao_que_existe(self):
        corpo = self._corpo_do_aviso()
        self.assertIn("Este vídeo é deste link", corpo)
        tela = _fonte("templates/index.html")
        self.assertIn('id="btnVincularAoLink"', tela,
                      "o aviso não pode citar um botão que não está na tela")

    def test_as_duas_situacoes_sao_ditas_com_as_mesmas_palavras(self):
        """'Cortando COM' e 'cortando SEM' precisam saltar aos olhos."""
        corpo = self._corpo_do_aviso()
        self.assertIn("CORTANDO COM O ACERVO", corpo)
        self.assertIn("CORTANDO SEM O ACERVO", corpo)

    def test_diz_quantos_cortes_o_acervo_preve(self):
        corpo = self._corpo_do_aviso()
        self.assertIn("possible_cuts", corpo,
                      "21 blocos e 55 cortes previstos é o que ele viu no Garimpo")

    def test_toda_saida_devolve_o_estado(self):
        """Quem chama grava o estado no relatório; devolver None o apaga."""
        corpo = self._corpo_do_aviso()
        arvore = ast.parse(corpo.strip())
        funcao = arvore.body[0]
        retornos = [n for n in ast.walk(funcao) if isinstance(n, ast.Return)]
        self.assertGreaterEqual(len(retornos), 3, "com acervo, sem id, e sem blocos")
        for retorno in retornos:
            self.assertIsNotNone(retorno.value, "um return vazio apaga o estado")


class OEstadoChegaNoRelatorio(unittest.TestCase):
    """A linha do console rola e some; o arquivo fica."""

    def test_o_seletor_copia_o_estado_para_o_diagnostico(self):
        from modules.clip_selector import ClipSelector

        seletor = ClipSelector(max_clips=5)
        estado = {"estado": "com_acervo", "available": True, "blocks": 21,
                  "highlights": 55, "possible_cuts": 55, "video_id": "tY62sQiv0-A"}
        transcricao = {"segments": [
            {"start": i * 15.0, "end": (i + 1) * 15.0, "text": f"Uma ideia número {i}."}
            for i in range(12)
        ]}

        seletor.select_clips(transcricao, settings={"acervo": estado})

        gravado = seletor.get_candidate_diagnostics()["acervo"]
        self.assertEqual(gravado["blocks"], 21)
        self.assertEqual(gravado["video_id"], "tY62sQiv0-A")
        self.assertEqual(gravado["estado"], "com_acervo")

    def test_sem_acervo_o_relatorio_diz_isso_em_vez_de_ficar_mudo(self):
        from modules.clip_selector import ClipSelector

        seletor = ClipSelector(max_clips=5)
        transcricao = {"segments": [
            {"start": i * 15.0, "end": (i + 1) * 15.0, "text": f"Uma ideia número {i}."}
            for i in range(12)
        ]}

        seletor.select_clips(transcricao, settings={})

        gravado = seletor.get_candidate_diagnostics()["acervo"]
        self.assertFalse(gravado["available"])
        self.assertEqual(gravado["estado"], "nao_verificado")


if __name__ == "__main__":
    unittest.main()

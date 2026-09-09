"""De que vídeo do YouTube é este arquivo — a etiqueta que o Furia apagava.

O DEFEITO, MEDIDO NOS ARQUIVOS DELE
------------------------------------
Tudo que liga o Furia ao Acervo do CHUB pendura em onze caracteres no nome do
arquivo. Só que o próprio Furia carimba um número ALEATÓRIO ao guardar
(`secrets.token_hex(6)`), e o id do YouTube morre ali:

    7 DE SETEMBRO - ATO CONTRA STF E TRAIDORES DA NAÇÃO_cecc818df5a8.mp4
                                                        ^^^^^^^^^^^^
                                                        aleatório, não é o id

Testado nos sete arquivos mais recentes dele: **seis não eram reconhecidos.**
O único que era veio baixado por fora, com o id no nome.

O QUE ISSO CUSTOU
-----------------
O ato de 7 de setembro é o `tY62sQiv0-A`. O CHUB tem, para esse vídeo:

    21 blocos revisados por gente
    55 momentos fortes
    810 frases com hora

E nenhuma das 7 fronteiras que o Furia escolheu bate com nenhuma das 21 —
porque ele nunca chegou a perguntar. Nas palavras do editor: o CHUB estava
sendo usado "apenas como enfeite de mesa".

AS DUAS PONTAS QUE FALTAVAM
---------------------------
O caderninho (`vinculos.json`) e a função `bind` existiam desde sempre. A
única porta para eles era `chub.bat --vincular "ARQUIVO" ID`, digitado num
terminal — e o editor não usa terminal. Capacidade construída, ligação
ausente: o mesmo formato de erro de todos os outros defeitos desta semana.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.acervo_library import (
    anotar_do_link,
    bound_id_for,
    resolved_id_for,
    youtube_id_from_name,
    youtube_id_from_url,
)


class LerOIdDeUmEndereco(unittest.TestCase):
    def test_o_link_que_ele_mandou(self):
        """Formato /live/ — é o de toda transmissão ao vivo, metade do material."""
        self.assertEqual(
            youtube_id_from_url("https://www.youtube.com/live/tY62sQiv0-A?is=Q0srA1RSO3mJ3Y6k"),
            "tY62sQiv0-A",
        )

    def test_os_outros_formatos(self):
        casos = {
            "https://www.youtube.com/watch?v=tY62sQiv0-A": "tY62sQiv0-A",
            "https://www.youtube.com/watch?v=tY62sQiv0-A&t=120s": "tY62sQiv0-A",
            "https://youtu.be/tY62sQiv0-A?t=12": "tY62sQiv0-A",
            "https://www.youtube.com/shorts/tY62sQiv0-A": "tY62sQiv0-A",
            "https://www.youtube.com/embed/tY62sQiv0-A": "tY62sQiv0-A",
            "youtu.be/tY62sQiv0-A": "tY62sQiv0-A",
        }
        for endereco, esperado in casos.items():
            self.assertEqual(youtube_id_from_url(endereco), esperado, endereco)

    def test_o_que_nao_e_endereco_do_youtube_nao_inventa_id(self):
        for lixo in ["", None, "https://vimeo.com/123456", "meu video.mp4",
                     "https://www.youtube.com/watch?v=curto"]:
            self.assertIsNone(youtube_id_from_url(lixo), repr(lixo))

    def test_nao_confunde_id_com_pedaco_de_outro_texto(self):
        self.assertIsNone(
            youtube_id_from_url("https://www.youtube.com/watch?v=tY62sQiv0-AXXXX"),
            "doze ou mais caracteres não é um id",
        )


class OsArquivosDeleVoltamAAcharOAcervo(unittest.TestCase):
    NOMES_DELE = [
        "7 DE SETEMBRO - ATO CONTRA STF E TRAIDORES DA NAÇÃO_cecc818df5a8.mp4",
        "TURNÊ DE CAMPANHA NO NORDESTE - CEARÁ [1_05_09-1_37_10]_9c059bd66918.mp4",
        "RENAN SANTOS - Flow News #065_cc1493ec853a.mp4",
        "VOLTAMOS - IRL RENAN SANTOS NA PAULISTA_137f8f6fa1a1.mp4",
        "COLETIVA DE IMPRENSA - PARTIDO MISSÃO_87b033c9f1ad.mp4",
    ]

    def setUp(self):
        self.raiz = Path(tempfile.mkdtemp(prefix="etiqueta-"))
        self.addCleanup(shutil.rmtree, self.raiz, ignore_errors=True)

    def test_o_nome_sozinho_nao_reconhece_nenhum_deles(self):
        """O estado de hoje, guardado para não voltar sem ninguém ver."""
        for nome in self.NOMES_DELE:
            self.assertIsNone(youtube_id_from_name(nome), nome)

    def test_depois_de_anotar_o_link_todos_sao_reconhecidos(self):
        for nome in self.NOMES_DELE:
            caminho = self.raiz / nome
            anotar_do_link(str(caminho), "https://www.youtube.com/live/tY62sQiv0-A",
                           data_dir=str(self.raiz))
            self.assertEqual(resolved_id_for(str(caminho), data_dir=str(self.raiz)),
                             "tY62sQiv0-A", nome)

    def test_o_caderninho_sobrevive_ao_programa_fechar(self):
        caminho = self.raiz / self.NOMES_DELE[0]
        anotar_do_link(str(caminho), "https://youtu.be/tY62sQiv0-A", data_dir=str(self.raiz))

        # Lido de novo do zero, como numa próxima abertura do programa.
        self.assertEqual(bound_id_for(str(caminho), data_dir=str(self.raiz)), "tY62sQiv0-A")

    def test_link_sem_id_nao_escreve_nada_e_nao_levanta(self):
        caminho = self.raiz / self.NOMES_DELE[0]
        self.assertIsNone(anotar_do_link(str(caminho), "https://vimeo.com/1", data_dir=str(self.raiz)))
        self.assertIsNone(bound_id_for(str(caminho), data_dir=str(self.raiz)))

    def test_o_nome_no_arquivo_continua_ganhando_quando_existe(self):
        """Nada que já funcionava pode passar a depender do caderninho."""
        nome = "Renan_Santos_no_Debate [OyfkLvZj9xk].mp4"
        self.assertEqual(resolved_id_for(str(self.raiz / nome), data_dir=str(self.raiz)),
                         "OyfkLvZj9xk")


class ODownloadAnotaSozinho(unittest.TestCase):
    """O único instante em que a origem existe de graça é o download."""

    def test_o_helper_do_download_anota_e_nunca_levanta(self):
        from modules.source_ingest import _anotar_a_origem

        raiz = Path(tempfile.mkdtemp(prefix="download-"))
        self.addCleanup(shutil.rmtree, raiz, ignore_errors=True)
        caminho = raiz / "video baixado_ab12cd34ef56.mp4"

        with patch("modules.acervo_library.library_dir", return_value=raiz):
            _anotar_a_origem(str(caminho), "https://www.youtube.com/live/tY62sQiv0-A?is=x")
            self.assertEqual(bound_id_for(str(caminho), data_dir=str(raiz)), "tY62sQiv0-A")

    def test_falhar_ao_anotar_nunca_derruba_um_download_que_deu_certo(self):
        from modules.source_ingest import _anotar_a_origem

        with patch("modules.acervo_library.anotar_do_link", side_effect=OSError("disco cheio")):
            _anotar_a_origem("/qualquer/video.mp4", "https://youtu.be/tY62sQiv0-A")

    def test_os_dois_downloads_chamam_o_helper(self):
        """Sem esta ligação a função existe e ninguém a chama — que é
        exatamente como o caderninho passou a vida inteira."""
        fonte = Path(__file__).resolve().parents[1] / "modules" / "source_ingest.py"
        texto = fonte.read_text(encoding="utf-8")
        self.assertEqual(texto.count("_anotar_a_origem("), 3,
                         "a definição mais as duas chamadas dos downloads")


class OBotaoEstaNaTelaELigado(unittest.TestCase):
    def test_o_botao_e_a_rota_existem(self):
        raiz = Path(__file__).resolve().parents[1]
        tela = (raiz / "templates" / "index.html").read_text(encoding="utf-8")
        script = (raiz / "static" / "js" / "app.js").read_text(encoding="utf-8")
        servidor = (raiz / "app.py").read_text(encoding="utf-8")

        self.assertIn('id="btnVincularAoLink"', tela)
        self.assertIn("/api/acervo/vincular", script)
        self.assertIn('@app.route("/api/acervo/vincular"', servidor)

    def test_a_tela_de_estado_le_o_caderninho(self):
        """Ela lia só o nome do arquivo, e dizia 'não reconhecido' para um
        arquivo já vinculado — o vínculo existia e a tela negava."""
        servidor = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        trecho = servidor.split('def api_acervo_status():')[1][:1200]
        self.assertIn("resolved_id_for", trecho)


if __name__ == "__main__":
    unittest.main()

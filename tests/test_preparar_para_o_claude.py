"""O botão que junta o que eu preciso para achar um defeito.

A PERGUNTA DELE QUE ORIGINOU ISTO
---------------------------------
    "mandei os arquivos certos antes ou faltou algum? e onde fica o arquivo de
     feedback dos aprovados e rejeitados para eu te mandar?"

Ele mandou cinco arquivos e acertou — por sorte, e dois eram cópia um do outro.
Os dois que resolveram moram em pastas DIFERENTES da máquina dele, e existia até
uma rota que abria a pasta de diagnóstico que **não tinha botão em tela
nenhuma** — ou seja, era como se não existisse.
"""

import json
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch


class PrepararParaOClaude(unittest.TestCase):
    def setUp(self):
        import app

        self.app = app
        self.cliente = app.app.test_client()

    def _bancada(self, tmp: Path, com_diagnostico=True, com_banco=True):
        (tmp / "diagnostics").mkdir(parents=True, exist_ok=True)
        if com_diagnostico:
            for nome in ("selecao-a.json", "selecao-b.json"):
                (tmp / "diagnostics" / nome).write_text(
                    json.dumps({"versao": "6.61"}), encoding="utf-8")
        banco = tmp / "database" / "editorial_learning.sqlite3"
        banco.parent.mkdir(parents=True, exist_ok=True)
        if com_banco:
            conexao = sqlite3.connect(banco)
            conexao.execute("CREATE TABLE clip_feedback (id INTEGER PRIMARY KEY, action TEXT)")
            conexao.execute("INSERT INTO clip_feedback (action) VALUES ('approved')")
            conexao.commit()
            conexao.close()
        return banco

    def _chamar(self, tmp, banco):
        with patch.dict("os.environ", {"FURIA_CLIPS_DATA_DIR": str(tmp)}), \
                patch.object(self.app, "DB_PATH", str(banco)), \
                patch.object(self.app, "open_local_path") as abrir:
            resposta = self.cliente.post("/api/preparar-para-o-claude")
        return resposta, abrir

    def test_junta_o_diagnostico_e_os_vereditos_numa_pasta_so(self):
        import tempfile

        with tempfile.TemporaryDirectory() as raiz:
            tmp = Path(raiz)
            banco = self._bancada(tmp)
            resposta, abrir = self._chamar(tmp, banco)

            self.assertEqual(resposta.status_code, 200)
            corpo = resposta.get_json()
            self.assertTrue(corpo["success"])
            destino = tmp / "para-o-claude"
            nomes = sorted(p.name for p in destino.iterdir())
            self.assertIn("editorial_learning.sqlite3", nomes,
                          "os vereditos são metade da resposta")
            self.assertTrue(any(n.startswith("selecao-") for n in nomes),
                            "o diagnóstico é a outra metade")
            abrir.assert_called_once()

    def test_a_copia_do_banco_e_um_banco_legivel(self):
        """Copiar arquivo vivo entrega banco pela metade; aqui usa o backup do sqlite."""
        import tempfile

        with tempfile.TemporaryDirectory() as raiz:
            tmp = Path(raiz)
            banco = self._bancada(tmp)
            self._chamar(tmp, banco)

            copia = tmp / "para-o-claude" / "editorial_learning.sqlite3"
            conexao = sqlite3.connect(copia)
            total = conexao.execute("SELECT COUNT(*) FROM clip_feedback").fetchone()[0]
            conexao.close()
            self.assertEqual(total, 1, "a cópia tem que abrir e ter os vereditos dentro")

    def test_sem_nada_para_mandar_a_resposta_diz_o_que_fazer(self):
        """Máquina nova: erro que ensina, não erro que assusta."""
        import tempfile

        with tempfile.TemporaryDirectory() as raiz:
            tmp = Path(raiz)
            banco = self._bancada(tmp, com_diagnostico=False, com_banco=False)
            resposta, abrir = self._chamar(tmp, banco)

            self.assertEqual(resposta.status_code, 404)
            self.assertIn("moa um vídeo", resposta.get_json()["error"])
            abrir.assert_not_called()

    def test_preparar_de_novo_nao_acumula_lixo(self):
        """A pasta é o que vale HOJE; sobra de ontem confunde quem arrasta."""
        import tempfile

        with tempfile.TemporaryDirectory() as raiz:
            tmp = Path(raiz)
            banco = self._bancada(tmp)
            destino = tmp / "para-o-claude"
            destino.mkdir(parents=True, exist_ok=True)
            (destino / "selecao-antiga-de-mes-passado.json").write_text("{}", encoding="utf-8")

            self._chamar(tmp, banco)
            self.assertFalse((destino / "selecao-antiga-de-mes-passado.json").exists())

    def test_o_botao_existe_na_tela_e_chama_a_rota(self):
        """Rota sem botão é rota que não existe — foi o que aconteceu antes."""
        raiz = Path(__file__).resolve().parents[1]
        tela = (raiz / "templates" / "index.html").read_text(encoding="utf-8")
        script = (raiz / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="btnPrepararParaOClaude"', tela)
        self.assertIn("/api/preparar-para-o-claude", script)


if __name__ == "__main__":
    unittest.main()

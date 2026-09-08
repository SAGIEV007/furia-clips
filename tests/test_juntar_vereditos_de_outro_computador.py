"""Trazer os vereditos do outro notebook, juntando em vez de substituir.

O QUE O EDITOR DISSE, DEPOIS DE DESCOBRIR QUE O SINCRONISMO NUNCA FUNCIONOU
---------------------------------------------------------------------------
    "não precisa ter essa interface de atualizar via github a versão do fúria já
     que não funciona mesmo, mas tem que ser realmente funcional a parte dos
     aprendizados também"

Ele está certo nas duas metades. Medido nos bancos que ele guardou dos outros
computadores:

    banco de hoje ............ 120 vereditos
    de um notebook antigo ..... 35 vereditos, NENHUM aqui dentro
    de outro ...................2 vereditos, NENHUM aqui dentro

Trinta e sete julgamentos parados em pasta. Com eles juntos, os casos que a
calibração conta vão de 79 para 102.
"""

import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch


def _banco(caminho: Path, vereditos, assinatura="video-a"):
    """Um banco com o esquema mínimo que a junção lê."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(caminho)
    conexao.executescript(
        "CREATE TABLE projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,"
        " source_video TEXT, source_signature TEXT);"
        "CREATE TABLE clips (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER,"
        " file_path TEXT, editorial_key TEXT, start_time REAL, end_time REAL,"
        " duration REAL, viral_score INTEGER, score_factors TEXT);"
        "CREATE TABLE clip_feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, clip_id INTEGER,"
        " action TEXT, reason_code TEXT, created_at TEXT);"
    )
    conexao.execute("INSERT INTO projects (id,name,source_video,source_signature)"
                    " VALUES (1,?,?,?)", ("V", "v.mp4", assinatura))
    for indice, (inicio, fim, acao, motivo, quando) in enumerate(vereditos, start=1):
        conexao.execute(
            "INSERT INTO clips (id,project_id,file_path,start_time,end_time,duration,"
            " viral_score,score_factors) VALUES (?,1,?,?,?,?,?,?)",
            (indice, "c.mp4", inicio, fim, fim - inicio, 70,
             '{"hook": 70, "_review_flags": {"payoff_complete": true,'
             ' "starts_mid_sentence": false, "context_complete": true,'
             ' "overlap_suspected": false}}'),
        )
        conexao.execute(
            "INSERT INTO clip_feedback (clip_id,action,reason_code,created_at)"
            " VALUES (?,?,?,?)", (indice, acao, motivo, quando))
    conexao.commit()
    conexao.close()


def _quantos(caminho):
    conexao = sqlite3.connect(caminho)
    total = conexao.execute("SELECT COUNT(*) FROM clip_feedback").fetchone()[0]
    conexao.close()
    return total


class JuntarVereditos(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.raiz = Path(tempfile.mkdtemp(prefix="juntar-"))
        self.addCleanup(__import__("shutil").rmtree, self.raiz, ignore_errors=True)
        self.aqui = self.raiz / "aqui.sqlite3"
        self.la = self.raiz / "la.sqlite3"
        _banco(self.aqui, [
            (10.0, 70.0, "rejected", "no_payoff", "2026-09-01 10:00:00"),
            (80.0, 140.0, "approved", "editor_approved", "2026-09-01 10:01:00"),
        ])
        _banco(self.la, [
            (10.0, 70.0, "rejected", "no_payoff", "2026-09-01 10:00:00"),   # igual
            (200.0, 260.0, "rejected", "starts_late", "2026-08-20 09:00:00"),
            (300.0, 360.0, "approved", "editor_approved", "2026-08-20 09:05:00"),
        ])

    def _juntar(self, de=None):
        import modules.aprendizado as ap

        with patch("config.DB_PATH", str(self.aqui)):
            return ap.juntar_vereditos_de(str(de or self.la))

    def test_traz_o_que_falta_e_reconhece_o_que_ja_existe(self):
        resumo = self._juntar()

        self.assertEqual(resumo["lidos"], 3)
        self.assertEqual(resumo["novos"], 2, "os dois do outro computador entram")
        self.assertEqual(resumo["ja_tinha"], 1, "o que já estava aqui não entra de novo")
        self.assertEqual(_quantos(self.aqui), 4)

    def test_importar_duas_vezes_da_o_mesmo_que_uma(self):
        """A primeira versão criava assinatura nova a cada importação.

        Com isso o mesmo veredito não era reconhecido no reimport e entrava em
        dobro — e veredito contado em dobro pesa em dobro na calibração, sem
        ninguém perceber.
        """
        self._juntar()
        depois_de_uma = _quantos(self.aqui)
        segundo = self._juntar()

        self.assertEqual(segundo["novos"], 0)
        self.assertEqual(segundo["ja_tinha"], 3)
        self.assertEqual(_quantos(self.aqui), depois_de_uma)

    def test_nada_do_que_estava_aqui_e_apagado(self):
        """Substituir joga fora o que ESTE computador julgou. Juntar não."""
        antes = _quantos(self.aqui)
        self._juntar()

        conexao = sqlite3.connect(self.aqui)
        sobrevivente = conexao.execute(
            "SELECT COUNT(*) FROM clip_feedback WHERE created_at = ?",
            ("2026-09-01 10:01:00",),
        ).fetchone()[0]
        conexao.close()
        self.assertEqual(sobrevivente, 1, "o veredito local continua aqui")
        self.assertGreater(_quantos(self.aqui), antes)

    def test_os_sinais_do_motor_vem_junto(self):
        """Sem os sinais, o veredito chega sem o que o motor achava.

        A calibração compara as duas coisas; um veredito sem manifesto é
        contado zero vezes — foi assim que 90 vereditos dele não moviam nada.
        """
        self._juntar()

        conexao = sqlite3.connect(self.aqui)
        conexao.row_factory = sqlite3.Row
        linha = conexao.execute(
            "SELECT c.score_factors FROM clips c JOIN clip_feedback f ON f.clip_id = c.id"
            " WHERE f.created_at = ?", ("2026-08-20 09:00:00",)).fetchone()
        conexao.close()
        self.assertIn("_review_flags", linha["score_factors"])

    def test_arquivo_que_nao_e_banco_do_furia_explica_em_portugues(self):
        qualquer = self.raiz / "qualquer.sqlite3"
        conexao = sqlite3.connect(qualquer)
        conexao.execute("CREATE TABLE outra_coisa (id INTEGER)")
        conexao.commit()
        conexao.close()

        with self.assertRaises(ValueError) as erro:
            self._juntar(qualquer)
        self.assertIn("banco do Furia", str(erro.exception))

    def test_arquivo_inexistente_nao_quebra(self):
        with self.assertRaises(FileNotFoundError):
            self._juntar(self.raiz / "nao-existe.sqlite3")

    def test_os_motivos_da_versao_antiga_continuam_valendo(self):
        """Veredito dele não pode valer menos por ser de uma versão antiga."""
        from modules.aprendizado import O_MENU_DA_TELA, etiqueta_do_motivo

        self.assertEqual(etiqueta_do_motivo("sem_payoff"), "fim")
        self.assertEqual(etiqueta_do_motivo("sem_contexto"), "contexto")
        self.assertEqual(etiqueta_do_motivo("no_payoff"), "fim", "o de hoje também")
        self.assertNotIn("sem_payoff", O_MENU_DA_TELA, (
            "nome antigo não pode entrar no menu de hoje: existe um teste que "
            "cobra uma opção na tela para cada item de lá"
        ))

    def test_o_botao_existe_na_tela_e_chama_a_rota(self):
        raiz = Path(__file__).resolve().parents[1]
        tela = (raiz / "templates" / "index.html").read_text(encoding="utf-8")
        script = (raiz / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="btnJuntarVereditos"', tela)
        self.assertIn('id="arquivoDeVereditos"', tela)
        self.assertIn("/api/editorial/juntar-vereditos", script)


if __name__ == "__main__":
    unittest.main()

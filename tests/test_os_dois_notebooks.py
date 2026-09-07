"""O feedback atravessando de um notebook para o outro, com git de verdade.

A PERGUNTA DO EDITOR QUE ORIGINOU ISTO
--------------------------------------
    "pode testar você mesmo se está funcionando? porque apesar do fúria ter a
     função de 'se atualizar' isso nunca funcionou então acho difícil"

A desconfiança era justificada e o defeito existia: `_branch` devolvia um nome
fixo de uma branch antiga, e "Enviar feedback ao GitHub" sempre dava erro. Os
outros testes desta pasta falsificam o `git` com `patch`, e por isso não
pegaram: um `git` de mentira aceita qualquer branch.

Aqui o `git` é o de verdade. Repositório bare local no lugar do GitHub, dois
checkouts no lugar dos dois notebooks, `push` e `pull` de verdade, e a conferência
no fim é o banco do segundo notebook — não o que a função devolveu sobre si mesma.
"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.repository_sync import (
    SNAPSHOT_RELATIVE_PATH,
    RepositorySyncError,
    push_feedback_snapshot,
    restore_feedback_snapshot,
)

BRANCH = "claude/repo-access-commits-imgjmk"
TEM_GIT = shutil.which("git") is not None


def _git(cwd, *args):
    resultado = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False,
        env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"},
    )
    if resultado.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} falhou:\n{resultado.stderr}")
    return resultado.stdout.strip()


def _banco(pasta_de_dados: Path, chaves, com_veredito: bool) -> Path:
    """Um banco com o ESQUEMA DE VERDADE, criado pelo `init_db` do programa.

    Escrever o esquema à mão aqui seria o mesmo erro dos testes com git
    falsificado: um esquema de mentira aceita coisas que o de verdade recusa.
    O `init_db` roda num processo à parte porque `config` resolve o caminho do
    banco na hora de importar.
    """
    pasta_de_dados.mkdir(parents=True, exist_ok=True)
    resultado = subprocess.run(
        [sys.executable, "-c", "import database; database.init_db(); print(database.DB_PATH)"],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True, text=True, check=False,
        env={**os.environ, "FURIA_CLIPS_DATA_DIR": str(pasta_de_dados)},
    )
    if resultado.returncode != 0:
        raise AssertionError(f"init_db falhou:\n{resultado.stderr}")
    caminho = Path(resultado.stdout.strip())

    conexao = sqlite3.connect(caminho)
    conexao.execute(
        "INSERT INTO projects (id, name, source_video, source_signature)"
        " VALUES (1, ?, ?, ?)", ("Live", "C:/v/live.mp4", "live-do-ceara"))
    for indice, chave in enumerate(chaves, start=1):
        conexao.execute(
            "INSERT INTO clips (id, project_id, file_path, editorial_key, start_time,"
            " end_time, duration, viral_score, editorial_score_version)"
            " VALUES (?,1,?,?,?,?,?,?,?)",
            (indice, f"C:/c/{indice}.mp4", chave, 10.0 * indice, 10.0 * indice + 60,
             60.0, 70 + indice, "v3"),
        )
        if com_veredito:
            acao = "approved" if indice % 2 else "rejected"
            conexao.execute(
                "INSERT INTO clip_feedback (clip_id, action, reason_code, quality_tags,"
                " adjustments, note, created_at) VALUES (?,?,?,?,?,?,?)",
                (indice, acao, "" if acao == "approved" else "no_payoff",
                 '["completo"]', '{"text": "SEGREDO QUE NAO PODE SAIR"}',
                 "anotação privada do editor", f"2026-09-0{indice} 12:00:00"),
            )
    conexao.commit()
    conexao.close()
    return caminho


@unittest.skipUnless(TEM_GIT, "precisa do git instalado")
class OsDoisNotebooks(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="dois-notebooks-"))
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        self.chaves = ["corte-aaa", "corte-bbb", "corte-ccc"]

        github = self.base / "github.git"
        _git(self.base, "init", "--bare", "-b", BRANCH, str(github))

        self.a = self.base / "notebook-A"
        self.a.mkdir()
        _git(self.a, "init", "-b", BRANCH)
        (self.a / "programa.txt").write_text("furia", encoding="utf-8")
        _git(self.a, "add", "-A")
        _git(self.a, "commit", "-q", "-m", "programa")
        _git(self.a, "remote", "add", "origin", str(github))
        _git(self.a, "push", "-q", "-u", "origin", BRANCH)

        self.b = self.base / "notebook-B"
        _git(self.base, "clone", "-q", str(github), str(self.b))

        self.banco_a = _banco(self.base / "dados-A", self.chaves, com_veredito=True)
        self.banco_b = _banco(self.base / "dados-B", self.chaves, com_veredito=False)

    @staticmethod
    def _abrir(caminho):
        """Igual ao `get_db` de verdade: linhas acessíveis por nome de coluna."""
        conexao = sqlite3.connect(caminho)
        conexao.row_factory = sqlite3.Row
        return conexao

    def _com_banco(self, caminho):
        return patch("modules.repository_sync.get_db",
                     side_effect=lambda: self._abrir(caminho))

    def _restaurar_em(self, caminho, repo):
        import database
        with patch.object(database, "get_db",
                          side_effect=lambda: self._abrir(caminho)):
            return restore_feedback_snapshot(str(repo))

    def test_o_veredito_sai_de_um_notebook_e_chega_no_outro(self):
        """A prova que os testes com git falsificado não davam.

        O que se confere no fim não é o que a função disse sobre si mesma: é o
        banco do notebook B, lido direto.
        """
        with self._com_banco(self.banco_a):
            enviado = push_feedback_snapshot(str(self.a))
        self.assertTrue(enviado["published"], "o envio tinha que publicar")
        self.assertEqual(enviado["record_count"], 3)
        self.assertEqual(enviado["branch"], BRANCH,
                         "o feedback tem que ir para a branch em que o programa está")

        _git(self.b, "pull", "-q", "origin", BRANCH)
        self.assertTrue((self.b / SNAPSHOT_RELATIVE_PATH).is_file(),
                        "o arquivo tinha que ter atravessado o GitHub")

        recebido = self._restaurar_em(self.banco_b, self.b)
        self.assertEqual(recebido["imported"], 3)
        self.assertEqual(recebido["unmatched"], 0)

        conexao = sqlite3.connect(self.banco_b)
        linhas = conexao.execute(
            "SELECT c.editorial_key, f.action FROM clip_feedback f"
            " JOIN clips c ON c.id = f.clip_id ORDER BY c.editorial_key").fetchall()
        conexao.close()
        self.assertEqual(
            linhas,
            [("corte-aaa", "approved"), ("corte-bbb", "rejected"), ("corte-ccc", "approved")],
            "os três vereditos tinham que estar no banco do outro notebook",
        )

    def test_nada_privado_atravessa_junto(self):
        """O repositório é público. O que vai no arquivo é só número e etiqueta."""
        with self._com_banco(self.banco_a):
            push_feedback_snapshot(str(self.a))
        bruto = (self.a / SNAPSHOT_RELATIVE_PATH).read_text(encoding="utf-8")

        self.assertNotIn("SEGREDO QUE NAO PODE SAIR", bruto)
        self.assertNotIn("anotação privada do editor", bruto)

        registro = json.loads(bruto)["records"][0]
        self.assertEqual(
            sorted(registro),
            ["action", "created_at", "duration_seconds", "editorial_key", "end_seconds",
             "quality_tags", "reason_code", "review_metadata", "score", "score_version",
             "source_signature", "start_seconds"],
            "campo novo no snapshot precisa ser conferido antes de ir para um repo público",
        )

    def test_apertar_duas_vezes_nao_publica_duas_vezes(self):
        """O segundo aperto tem que dizer 'já estava sincronizado', não falhar."""
        with self._com_banco(self.banco_a):
            push_feedback_snapshot(str(self.a))
            _git(self.a, "pull", "-q", "--rebase", "origin", BRANCH)
            segundo = push_feedback_snapshot(str(self.a))
        self.assertFalse(segundo["published"])

    def test_restaurar_sem_arquivo_explica_em_portugues(self):
        """Notebook novo, antes de qualquer envio: erro claro, não exceção crua."""
        with self.assertRaises(RepositorySyncError) as erro:
            self._restaurar_em(self.banco_b, self.b)
        self.assertIn("snapshot", str(erro.exception).lower())

    def test_mudanca_local_no_codigo_impede_a_publicacao(self):
        """A trava que evita o botão empurrar código junto com o feedback."""
        (self.a / "programa.txt").write_text("mexido à mão", encoding="utf-8")
        with self._com_banco(self.banco_a), self.assertRaises(RepositorySyncError) as erro:
            push_feedback_snapshot(str(self.a))
        self.assertIn("alterações locais", str(erro.exception))


if __name__ == "__main__":
    unittest.main()

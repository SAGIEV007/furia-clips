"""Moer o mesmo vídeo de novo escondia até o que ele tinha aprovado.

O DEFEITO, MEDIDO NO ATO DE 7 DE SETEMBRO
------------------------------------------
Segunda moagem da mesma fonte, lido do arquivo de diagnóstico que o próprio
programa salvou (`selecao7_DE_SETEMBRO...json`):

    45 candidatos
    30  depois do filtro de não-conteúdo
    23  depois da peneira de sobreposição
     7  POR JÁ TER MOÍDO ANTES        <- dezesseis caíram aqui
     2  entregues

    previous_discarded_count: 16
    previous_discarded_approved: 6      <- ELE TINHA APROVADO
    previous_discarded_rejected: 8

Nas palavras dele: "rendeu apenas 2 cortes infelizmente".

Esconder um corte porque ele já saiu antes trata "já saiu" como defeito. Não
é. O que manda é o veredito:

    rejeitou ......  esconde. Ele já disse não.
    aprovou .......  mostra. Ele disse SIM.
    não julgou ....  mostra. Ninguém decidiu nada.

E O VEREDITO PRECISA VIR DO LUGAR CERTO
----------------------------------------
`clips.review_status` só é preenchido quando ele decide NESTA máquina, pela
tela. Vereditos trazidos do outro notebook ficam em `clip_feedback` e não
mexem no estado do corte: no banco dele, 111 dos 169. Ler o campo errado é
esconder o aprovado e mostrar o rejeitado — ao contrário do que ele quer.

Por isso o teste do banco abaixo grava o veredito como a junção entre
computadores grava: só em `clip_feedback`, sem tocar em `review_status`.
"""

import unittest

import database
from modules.clip_selector import ClipSelector


def _seletor(anteriores):
    seletor = ClipSelector.__new__(ClipSelector)
    seletor._previous_clip_fingerprints = anteriores
    seletor._candidate_diagnostics = {
        "previous_discarded_count": 0,
        "previous_discarded_approved": 0,
        "previous_discarded_rejected": 0,
        "previous_kept_approved": 0,
        "previous_kept_unjudged": 0,
        "hard_negatives": [],
    }
    seletor._record_hard_negative = lambda *a, **k: None
    return seletor


def _corte(inicio, fim, texto="o Renan falando alguma coisa aqui"):
    return {"start": inicio, "end": fim, "duration": fim - inicio, "text": texto}


class OVereditoDeleEQuemManda(unittest.TestCase):
    def test_o_que_ele_aprovou_volta_para_a_mesa(self):
        anterior = {"start": 100.0, "end": 160.0, "duration": 60.0,
                    "text": "o Renan falando alguma coisa aqui",
                    "review_status": "approved"}
        seletor = _seletor([anterior])

        sobraram = seletor._remove_previous_fingerprints([_corte(100.0, 160.0)])

        self.assertEqual(len(sobraram), 1, "ele aprovou; esconder é jogar fora o que presta")
        self.assertTrue(sobraram[0]["ja_saiu_antes"])
        self.assertEqual(sobraram[0]["veredito_anterior"], "approved")
        self.assertEqual(seletor._candidate_diagnostics["previous_kept_approved"], 1)
        self.assertEqual(seletor._candidate_diagnostics["previous_discarded_count"], 0)

    def test_o_que_ele_rejeitou_continua_escondido(self):
        anterior = {"start": 100.0, "end": 160.0, "duration": 60.0,
                    "text": "o Renan falando alguma coisa aqui",
                    "review_status": "rejected"}
        seletor = _seletor([anterior])

        sobraram = seletor._remove_previous_fingerprints([_corte(100.0, 160.0)])

        self.assertEqual(sobraram, [], "ele já disse não uma vez")
        self.assertEqual(seletor._candidate_diagnostics["previous_discarded_count"], 1)
        self.assertEqual(seletor._candidate_diagnostics["previous_discarded_rejected"], 1)

    def test_o_que_ninguem_julgou_volta_para_a_mesa(self):
        anterior = {"start": 100.0, "end": 160.0, "duration": 60.0,
                    "text": "o Renan falando alguma coisa aqui",
                    "review_status": "pending"}
        seletor = _seletor([anterior])

        sobraram = seletor._remove_previous_fingerprints([_corte(100.0, 160.0)])

        self.assertEqual(len(sobraram), 1)
        self.assertEqual(seletor._candidate_diagnostics["previous_kept_unjudged"], 1)

    def test_corte_novo_passa_sem_carimbo_nenhum(self):
        anterior = {"start": 100.0, "end": 160.0, "duration": 60.0,
                    "text": "outra coisa completamente diferente",
                    "review_status": "rejected"}
        seletor = _seletor([anterior])

        sobraram = seletor._remove_previous_fingerprints([_corte(900.0, 960.0)])

        self.assertEqual(len(sobraram), 1)
        self.assertNotIn("ja_saiu_antes", sobraram[0])

    def test_o_numero_do_7_de_setembro(self):
        """Os 16 daquela moagem: 8 rejeitados somem, 6 aprovados e 2 sem
        veredito voltam. De 7 candidatos para 15."""
        anteriores, candidatos = [], []
        for n in range(16):
            inicio = 100.0 + n * 200
            estado = "rejected" if n < 8 else ("approved" if n < 14 else "pending")
            anteriores.append({"start": inicio, "end": inicio + 60, "duration": 60.0,
                               "text": f"trecho {n}", "review_status": estado})
            candidatos.append(_corte(inicio, inicio + 60, f"trecho {n}"))
        # mais sete que nunca saíram, como na moagem real
        for n in range(7):
            candidatos.append(_corte(9000.0 + n * 200, 9060.0 + n * 200, f"novo {n}"))

        seletor = _seletor(anteriores)
        sobraram = seletor._remove_previous_fingerprints(candidatos)

        self.assertEqual(len(sobraram), 15, "7 antes; agora 8 voltam para a mesa")
        self.assertEqual(seletor._candidate_diagnostics["previous_discarded_count"], 8)
        self.assertEqual(seletor._candidate_diagnostics["previous_kept_approved"], 6)


class OVereditoVemDoLugarCerto(unittest.TestCase):
    """O banco precisa devolver o veredito que ELE deu, não o estado do corte."""

    def _banco(self, monkeypatch, tmp_path):
        monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "furia.sqlite"))
        database.init_db()
        return database.create_project("Ato", "workspace/uploads/ato.mp4")

    def test_veredito_trazido_do_outro_notebook_e_respeitado(self):
        """É assim que a junção entre computadores grava: só clip_feedback."""
        import tempfile, shutil
        from pathlib import Path
        from unittest.mock import patch

        pasta = Path(tempfile.mkdtemp(prefix="fingerprints-"))
        self.addCleanup(shutil.rmtree, pasta, ignore_errors=True)

        with patch.object(database, "DB_PATH", str(pasta / "furia.sqlite")):
            database.init_db()
            projeto = database.create_project("Ato", "workspace/uploads/ato.mp4")
            corte = database.save_clip(projeto, "workspace/exports/c.mp4",
                                       100.0, 160.0, 60.0, viral_score=70)
            # SEM tocar em review_status — como a importação grava.
            database.save_clip_feedback(corte, "approved", reason_code="editor_approved")

            digitais = database.get_existing_clip_fingerprints("workspace/uploads/ato.mp4")

        self.assertEqual(len(digitais), 1)
        self.assertEqual(digitais[0]["review_status"], "approved",
                         "sem isto o aprovado dele seria lido como 'pending'")

    def test_ele_mudou_de_ideia_e_o_mais_novo_ganha(self):
        import tempfile, shutil
        from pathlib import Path
        from unittest.mock import patch

        pasta = Path(tempfile.mkdtemp(prefix="fingerprints2-"))
        self.addCleanup(shutil.rmtree, pasta, ignore_errors=True)

        with patch.object(database, "DB_PATH", str(pasta / "furia.sqlite")):
            database.init_db()
            projeto = database.create_project("Ato", "workspace/uploads/ato.mp4")
            corte = database.save_clip(projeto, "workspace/exports/c.mp4",
                                       100.0, 160.0, 60.0, viral_score=70)
            database.update_clip_review_status(corte, "approved")
            database.save_clip_feedback(corte, "rejected", reason_code="no_payoff")

            digitais = database.get_existing_clip_fingerprints("workspace/uploads/ato.mp4")

        self.assertEqual(digitais[0]["review_status"], "rejected")


if __name__ == "__main__":
    unittest.main()

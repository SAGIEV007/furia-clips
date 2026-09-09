"""O placar contra o CHUB, num botão — porque terminal ele não usa.

DE ONDE VEIO
------------
Eu terminei uma entrega dizendo a ele: "roda `python scripts/regua_assuntos.py
--pelo-modelo`". Ele respondeu:

    "esse código é para rodar onde??"

A pergunta estava certa e o erro era meu. A regra desta casa é antiga: se ele
precisa de alguma coisa, existe um botão. O número já existia; a porta para ele
não.

O QUE ESTE ARQUIVO PROTEGE
--------------------------
Um defeito que quase passou: o export convertido do Acervo guarda `start_s`, e
eu escrevi `start`. Nada levantava — o placar simplesmente diria 0 de 0, com ar
de resposta. Placar que erra em silêncio é pior do que placar nenhum.

E o cuidado que vale mais que o número: as fronteiras do CHUB são GABARITO,
nunca entrada. Se o Furia cortasse por elas e fosse medido contra elas, o número
subiria sem o corte melhorar.
"""

import unittest

from modules.placar_das_fronteiras import _numero, _viradas, comparar, do_acervo


def _export(blocos, frases, chave="start_s"):
    """Um export no formato que `convert` produz."""
    return {
        "records": {
            "sources": [{"title": "Ato de 7 de setembro", "youtube_id": "tY62sQiv0-A"}],
            "blocks": [{chave: inicio, "title": f"assunto {n}"}
                       for n, inicio in enumerate(blocos, start=1)],
            "sentences": [
                {chave: comeco, chave.replace("start", "end"): comeco + 4.0,
                 "text": f"frase aos {comeco} segundos", "speaker_change": False}
                for comeco in frases
            ],
        }
    }


class LerOsNomesCertosDosCampos(unittest.TestCase):
    def test_o_export_de_verdade_usa_start_s(self):
        """Foi o defeito que quase passou: ler `start` devolvia 0 de 0."""
        material = do_acervo_de(_export([0.0, 100.0, 200.0], [0.0, 4.0, 8.0]))
        self.assertEqual(len(material["blocos"]), 3)
        self.assertEqual(material["blocos"][0]["start"], 0.0)
        self.assertEqual(len(material["frases"]), 3)

    def test_o_gabarito_da_bancada_usa_start_e_tambem_entra(self):
        material = do_acervo_de(_export([0.0, 100.0], [0.0, 4.0], chave="start"))
        self.assertEqual(len(material["blocos"]), 2)
        self.assertEqual(len(material["frases"]), 2)

    def test_numero_ignora_o_que_nao_da_para_ler(self):
        self.assertEqual(_numero({"start_s": "12.5"}, "start_s", "start"), 12.5)
        self.assertIsNone(_numero({"start_s": "abacaxi"}, "start_s", "start"))
        self.assertIsNone(_numero({}, "start_s", "start"))
        self.assertIsNone(_numero({"start_s": None}, "start_s", "start"))

    def test_a_mesma_frase_em_dois_blocos_entra_uma_vez(self):
        """Os blocos trazem as frases deles, e a linha do tempo vem junto: sem
        isto a mesma frase entrava em dobro e a coesão lia repetição."""
        bruto = _export([0.0], [0.0, 4.0])
        bruto["records"]["sentences"] += list(bruto["records"]["sentences"])
        self.assertEqual(len(do_acervo_de(bruto)["frases"]), 2)

    def test_arquivo_que_nao_e_export_devolve_vazio_sem_levantar(self):
        self.assertEqual(do_acervo("/caminho/que/nao/existe.json"), {})


class AConta(unittest.TestCase):
    def test_o_comeco_do_video_nao_conta_como_virada(self):
        """Todo mundo acerta o zero; contá-lo infla os dois lados."""
        self.assertEqual(_viradas([0.0, 100.0, 200.0]), [100.0, 200.0])
        self.assertEqual(_viradas([]), [])
        self.assertEqual(_viradas([50.0]), [])

    def test_dentro_da_tolerancia_conta_como_achada(self):
        placar = comparar([100.0, 300.0], [104.0, 500.0])
        self.assertEqual(placar["achadas"], 1)
        self.assertEqual(placar["detalhe"][0]["erro_s"], 4.0)
        self.assertTrue(placar["detalhe"][0]["achou"])
        self.assertFalse(placar["detalhe"][1]["achou"])

    def test_a_coluna_anti_chute(self):
        """Achadas sozinha se conserta propondo mais. Quem chuta uma virada a
        cada dez segundos acha todas e não sabe nada."""
        chutador = comparar([100.0, 300.0], [float(n) for n in range(0, 400, 10)])
        self.assertEqual(chutador["achadas"], 2, "achou as duas, chutando")
        self.assertLess(chutador["certeiras_pct"], 20.0, "e a coluna anti-chute denuncia")

    def test_sem_nenhuma_proposta_o_placar_e_zero_e_nao_quebra(self):
        placar = comparar([100.0, 300.0], [])
        self.assertEqual(placar["achadas"], 0)
        self.assertEqual(placar["certeiras_pct"], 0.0)
        self.assertIsNone(placar["detalhe"][0]["furia_s"])


class OBotaoExisteEEstaLigado(unittest.TestCase):
    """Sem isto o placar existe e ninguém o alcança — que é exatamente o
    problema que ele apontou quando eu mandei rodar no terminal."""

    def test_botao_rota_e_tela(self):
        from pathlib import Path

        raiz = Path(__file__).resolve().parents[1]
        tela = (raiz / "templates" / "index.html").read_text(encoding="utf-8")
        script = (raiz / "static" / "js" / "app.js").read_text(encoding="utf-8")
        servidor = (raiz / "app.py").read_text(encoding="utf-8")

        self.assertIn('id="btnPlacarDasFronteiras"', tela)
        self.assertIn("/api/acervo/placar", script)
        self.assertIn('@app.route("/api/acervo/placar"', servidor)

    def test_a_rota_mede_o_mesmo_caminho_da_moagem(self):
        """Medir uma cópia do caminho foi como quatro defeitos desta semana
        passaram pelos testes."""
        from pathlib import Path

        servidor = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        trecho = servidor.split("def api_acervo_placar():")[1][:1600]
        self.assertIn("_settings_da_moagem = get_all_settings()", trecho,
                      "sem os ajustes dele o placar mede outra coisa")


class OPlacarPontaAPonta(unittest.TestCase):
    def test_do_export_ao_numero(self):
        import json
        import shutil
        import tempfile
        from pathlib import Path

        from modules.clip_selector import ClipSelector
        from modules.placar_das_fronteiras import medir_fonte

        pasta = Path(tempfile.mkdtemp(prefix="placar-"))
        self.addCleanup(shutil.rmtree, pasta, ignore_errors=True)

        # Duas metades com vocabulário bem distinto, para haver o que achar.
        frases = []
        for n in range(60):
            frases.append({"start_s": n * 6.0, "end_s": n * 6.0 + 6.0,
                           "text": f"O imposto e a reforma travam o orçamento no ponto {n}."})
        for n in range(60, 120):
            frases.append({"start_s": n * 6.0, "end_s": n * 6.0 + 6.0,
                           "text": f"A segurança e a polícia enfrentam o crime na cidade {n}."})
        export = {"records": {
            "sources": [{"title": "Fonte de teste", "youtube_id": "abc"}],
            "blocks": [{"start_s": 0.0, "title": "Imposto"},
                       {"start_s": 360.0, "title": "Segurança"}],
            "sentences": frases,
        }}
        caminho = pasta / "abc.json"
        caminho.write_text(json.dumps(export), encoding="utf-8")

        seletor = ClipSelector(min_duration=15, max_duration=180, max_clips=12)
        seletor._settings_da_moagem = {}
        seletor._candidate_diagnostics = {}
        placar = medir_fonte(caminho, seletor)

        self.assertTrue(placar["disponivel"])
        self.assertEqual(placar["blocos_do_chub"], 2)
        self.assertEqual(placar["viradas_no_gabarito"], 1)
        self.assertEqual(placar["origem"], "coesao_local")
        self.assertIn("achadas", placar)

    def test_video_sem_blocos_diz_isso_em_vez_de_dar_zero(self):
        import json
        import shutil
        import tempfile
        from pathlib import Path

        from modules.clip_selector import ClipSelector
        from modules.placar_das_fronteiras import medir_fonte

        pasta = Path(tempfile.mkdtemp(prefix="placar2-"))
        self.addCleanup(shutil.rmtree, pasta, ignore_errors=True)
        caminho = pasta / "vazio.json"
        caminho.write_text(json.dumps({"records": {"blocks": [], "sentences": []}}),
                           encoding="utf-8")

        seletor = ClipSelector(max_clips=5)
        seletor._settings_da_moagem = {}
        seletor._candidate_diagnostics = {}
        placar = medir_fonte(caminho, seletor)

        self.assertFalse(placar["disponivel"])
        self.assertIn("não tem blocos", placar["motivo"])


def do_acervo_de(payload):
    """Escreve o export num arquivo e lê, para exercitar o caminho de verdade."""
    import json
    import tempfile
    from pathlib import Path

    caminho = Path(tempfile.mkdtemp(prefix="export-")) / "x.json"
    caminho.write_text(json.dumps(payload), encoding="utf-8")
    return do_acervo(caminho)


if __name__ == "__main__":
    unittest.main()

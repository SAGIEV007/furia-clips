"""Moer o mesmo vídeo de novo devolvia quase nada, e a tela não dizia por quê.

A RECLAMAÇÃO DO EDITOR QUE ORIGINOU ISTO
----------------------------------------
    "ficou péssimo o resultado (...) onde consegui VÁRIOS cortes, dessa vez com
     a sua nova atualização, eu consegui 2"

Ele moeu de novo o ato de 7 de setembro para conferir uma mudança do motor —
porque eu pedi que conferisse. Lido no arquivo de diagnóstico que o próprio
programa salvou daquela moagem:

    45 candidatos -> 30 (filtro de não-conteúdo) -> 23 (sobreposição)
        -> 7 POR JÁ TER MOÍDO ANTES -> 2 entregues

    previous_discarded_count      16
    previous_discarded_approved    6   <- ele mesmo já tinha aprovado

Dezesseis caíram num passo só. A tela dizia "19 intervalos já gerados serão
evitados" — verdade, e inútil: ninguém liga aquela frase a "por isso vieram
dois". O motor não estava pior; estava proibido de repetir o que já tinha feito.

Evitar repetição está certo ao moer material novo, e errado ao moer o MESMO
vídeo de novo para comparar versões.
"""

import unittest


class OAvisoAntesDeMoer(unittest.TestCase):
    def test_quando_ha_o_que_evitar_o_aviso_ensina_a_desligar(self):
        from app import _avisos_da_deduplicacao

        avisos = _avisos_da_deduplicacao(
            {"previous_clip_fingerprints": [{}] * 19}, evitar_repetidos=True
        )
        self.assertEqual(len(avisos), 1)
        texto, nivel = avisos[0]
        self.assertIn("19", texto)
        self.assertIn("desligue", texto.lower())
        self.assertEqual(nivel, "warning", "isto muda o resultado; não é recado de rodapé")

    def test_com_a_deduplicacao_desligada_a_tela_diz_que_esta_desligada(self):
        from app import _avisos_da_deduplicacao

        avisos = _avisos_da_deduplicacao({"previous_clip_fingerprints": []}, evitar_repetidos=False)
        self.assertEqual(len(avisos), 1)
        self.assertIn("do zero", avisos[0][0])

    def test_fonte_moida_pela_primeira_vez_nao_ganha_recado(self):
        """Vídeo novo não tem nada a evitar; recado à toa vira ruído."""
        from app import _avisos_da_deduplicacao

        self.assertEqual(
            _avisos_da_deduplicacao({"previous_clip_fingerprints": []}, evitar_repetidos=True), []
        )


class AContaDepoisDeMoer(unittest.TestCase):
    def test_a_tela_diz_quantos_cortes_a_deduplicacao_levou(self):
        """O número existia só dentro de um JSON, e número assim ninguém lê."""
        from app import _quanto_custou_a_deduplicacao

        avisos = _quanto_custou_a_deduplicacao({
            "previous_discarded_count": 16,
            "previous_discarded_approved": 6,
            "previous_discarded_rejected": 8,
        })
        self.assertEqual(len(avisos), 1)
        texto, nivel = avisos[0]
        self.assertIn("16", texto)
        self.assertIn("6", texto)
        self.assertIn("aprovado", texto)
        self.assertEqual(nivel, "warning", "descartar corte aprovado por ele é aviso, não nota")

    def test_sem_descarte_nao_ha_conta_a_dar(self):
        from app import _quanto_custou_a_deduplicacao

        self.assertEqual(_quanto_custou_a_deduplicacao({}), [])
        self.assertEqual(_quanto_custou_a_deduplicacao({"previous_discarded_count": 0}), [])

    def test_descarte_so_de_rejeitados_e_informacao_e_nao_alarme(self):
        from app import _quanto_custou_a_deduplicacao

        avisos = _quanto_custou_a_deduplicacao({
            "previous_discarded_count": 4, "previous_discarded_rejected": 4,
        })
        self.assertEqual(avisos[0][1], "info")


class OBotaoDeMoerDoZero(unittest.TestCase):
    def test_a_opcao_existe_na_tela_e_e_enviada_no_pedido(self):
        """Ele não abre pasta nem digita comando: se precisa de um ajuste, é botão."""
        from pathlib import Path

        raiz = Path(__file__).resolve().parents[1]
        tela = (raiz / "templates" / "index.html").read_text(encoding="utf-8")
        script = (raiz / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="moerDoZero"', tela, "sem a caixa na tela ele não consegue ligar")
        self.assertIn("moer_do_zero", script, "a caixa tem que chegar no pedido de corte")

    def test_o_pedido_desliga_a_deduplicacao_no_motor(self):
        from pathlib import Path

        codigo = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        self.assertEqual(
            codigo.count('moer_do_zero = _coerce_bool(data.get("moer_do_zero"), default=False)'), 2,
            "as duas telas que moem precisam da mesma opção",
        )
        self.assertEqual(
            codigo.count('settings["evitar_ja_gerados"] = False'), 2,
            "ligar a caixa tem que desligar a deduplicação nos dois caminhos",
        )
        # Só a assinatura da função pode trazer o padrão. Quem CHAMA tem que
        # passar a escolha dele: fixar em True de novo tira a opção da tela sem
        # nenhum erro aparecer.
        chamadas_fixas = codigo.count("                allow_previous=True,")
        self.assertEqual(chamadas_fixas, 0, "nenhuma moagem pode fixar allow_previous")
        self.assertEqual(
            codigo.count("allow_previous=evitar_repetidos,"), 2,
            "as duas moagens têm que respeitar a escolha dele",
        )


if __name__ == "__main__":
    unittest.main()

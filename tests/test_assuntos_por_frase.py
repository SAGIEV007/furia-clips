"""Pedir as fronteiras pelo NÚMERO DA FRASE, e o vídeo inteiro de uma vez.

DE ONDE VEIO
------------
O editor mandou o link de um bloco do Garimpo e perguntou por que o Furia não
chega perto do que o CHUB faz com um vídeo que nem foi baixado. A resposta
estava nos dados do próprio CHUB, no ato de 7 de setembro:

    promptVersion: fronteiras-pt-v7h-min15 + correcoes + consolidacao + descricao
    startSentenceIdx: 4 · endSentenceIdx: 98
    providerId: openrouter:openai/gpt-5.6-luna

O CHUB numera as 810 frases do vídeo e pergunta ao modelo onde cada assunto
começa PELO NÚMERO DA FRASE. O horário sai da tabela de frases; ninguém o
inventa. Por isso as 21 fronteiras dele caem no lugar.

O Furia mandava OITO blocos de 50–90 s por vez — uma fresta de oito minutos num
vídeo de sessenta — e pedia HORÁRIOS, que o modelo inventava.

O QUE ESTE ARQUIVO PODE E NÃO PODE PROVAR
------------------------------------------
Pode provar que o pedido leva o vídeo inteiro, que a resposta é conferida antes
de valer, que a borda cai no começo exato de uma frase e que a falha do modelo
cai na leitura local em vez de derrubar a moagem.

NÃO pode provar que o Gemini divide bem. Isso só se mede na máquina dele, com
chave, contra o gabarito do Acervo — `python scripts/regua_assuntos.py`. Um
teste com modelo de mentira que "acerta" mediria a minha mentira.
"""

import json
import unittest

from modules.assuntos_por_frase import (
    MINIMO_DE_FRASES,
    assuntos_por_modelo,
    ler_resposta,
    montar_pedido,
    numerar,
)


def _frases(quantas, passo=4.0):
    return [
        {"start": n * passo, "end": (n + 1) * passo,
         "text": f"Frase número {n} sobre alguma coisa do país."}
        for n in range(quantas)
    ]


class ATabelaDeFrases(unittest.TestCase):
    def test_cada_frase_ganha_endereco_fixo(self):
        tabela = numerar(_frases(5))
        self.assertEqual([f["idx"] for f in tabela], [0, 1, 2, 3, 4])

    def test_frase_vazia_ou_torta_nao_entra_e_nao_quebra(self):
        tabela = numerar([
            {"start": 0.0, "end": 4.0, "text": "vale"},
            {"start": 0.0, "end": 4.0, "text": "   "},
            {"start": 9.0, "end": 5.0, "text": "fim antes do começo"},
            {"start": "x", "end": 4.0, "text": "hora ilegível"},
        ])
        self.assertEqual(len(tabela), 1)


class OPedidoLevaOVideoInteiro(unittest.TestCase):
    def test_toda_frase_aparece_numerada(self):
        """A fresta de oito minutos era o defeito; o pedido é o vídeo todo."""
        tabela = numerar(_frases(300))
        pedido = montar_pedido(tabela)

        for indice in (0, 42, 150, 299):
            self.assertIn(f"[{indice}]", pedido, f"a frase {indice} ficou de fora")

    def test_pede_numero_de_frase_e_nao_horario(self):
        pedido = montar_pedido(numerar(_frases(40)))
        self.assertIn("NÚMERO da primeira e da última frase", pedido)
        self.assertIn("nunca com horário", pedido)

    def test_leva_o_minimo_de_frases_por_assunto(self):
        pedido = montar_pedido(numerar(_frases(40)))
        self.assertIn(f"pelo menos {MINIMO_DE_FRASES} frases", pedido)

    def test_marca_onde_quem_fala_muda(self):
        frases = _frases(40)
        frases[20]["speaker_change"] = True
        pedido = montar_pedido(numerar(frases))
        self.assertIn("[20] 1:20 >>", pedido)


class ARespostaDoModeloEConferida(unittest.TestCase):
    """Nada aqui confia no modelo. Bloco inventado é pior que bloco a menos."""

    def test_o_caso_normal(self):
        blocos = ler_resposta(
            '{"assuntos":[{"inicio":0,"fim":29,"titulo":"Imposto","conteudo":true},'
            '{"inicio":30,"fim":59,"titulo":"Segurança","conteudo":false}]}', total=60)
        self.assertEqual(len(blocos), 2)
        self.assertEqual(blocos[0]["titulo"], "Imposto")
        self.assertFalse(blocos[1]["conteudo"])

    def test_endereco_fora_da_transcricao_e_descartado(self):
        blocos = ler_resposta(
            '{"assuntos":[{"inicio":0,"fim":29},{"inicio":30,"fim":900}]}', total=60)
        self.assertEqual(len(blocos), 1, "a frase 900 não existe")

    def test_bloco_curto_demais_e_descartado(self):
        blocos = ler_resposta(
            '{"assuntos":[{"inicio":0,"fim":2},{"inicio":10,"fim":40}]}', total=60)
        self.assertEqual(len(blocos), 1, "três frases não são um assunto")

    def test_blocos_que_se_sobrepoem_nao_passam_os_dois(self):
        blocos = ler_resposta(
            '{"assuntos":[{"inicio":0,"fim":40},{"inicio":20,"fim":59}]}', total=60)
        self.assertEqual(len(blocos), 1)

    def test_cerca_de_markdown_nao_atrapalha(self):
        blocos = ler_resposta(
            '```json\n{"assuntos":[{"inicio":0,"fim":29}]}\n```', total=60)
        self.assertEqual(len(blocos), 1)

    def test_resposta_que_nao_e_json_devolve_vazio_em_vez_de_levantar(self):
        for lixo in ["desculpe, não consegui", "", "{quebrado", "[]", "null"]:
            self.assertEqual(ler_resposta(lixo, total=60), [], repr(lixo))


class ABordaCaiNoComecoDeUmaFrase(unittest.TestCase):
    """O ponto de tudo isto: a hora vem da tabela, não do modelo."""

    def test_o_inicio_e_o_fim_saem_da_tabela_de_frases(self):
        frases = _frases(60)
        resposta = json.dumps({"assuntos": [
            {"inicio": 0, "fim": 29, "titulo": "Um"},
            {"inicio": 30, "fim": 59, "titulo": "Dois"},
        ]})

        unidades = assuntos_por_modelo(frases, lambda _: resposta, corrigir=False)

        self.assertEqual(len(unidades), 2)
        self.assertEqual(unidades[0]["start_s"], frases[0]["start"])
        self.assertEqual(unidades[0]["end_s"], frases[29]["end"])
        self.assertEqual(unidades[1]["start_s"], frases[30]["start"])
        self.assertEqual(unidades[1]["primeira_frase"], 30)

    def test_o_endereco_da_frase_viaja_junto(self):
        """É o que deixa cada corte dizer de onde a borda dele nasceu."""
        unidades = assuntos_por_modelo(
            _frases(60),
            lambda _: '{"assuntos":[{"inicio":5,"fim":40,"titulo":"Tese"}]}',
            corrigir=False)
        self.assertEqual(unidades[0]["primeira_frase"], 5)
        self.assertEqual(unidades[0]["ultima_frase"], 40)
        self.assertEqual(unidades[0]["origem"], "modelo_por_frase")


class ASegundaPassada(unittest.TestCase):
    def test_a_correcao_substitui_a_primeira_divisao(self):
        respostas = iter([
            '{"assuntos":[{"inicio":0,"fim":59,"titulo":"tudo junto"}]}',
            '{"assuntos":[{"inicio":0,"fim":29,"titulo":"Um"},'
            '{"inicio":30,"fim":59,"titulo":"Dois"}]}',
        ])
        unidades = assuntos_por_modelo(_frases(60), lambda _: next(respostas))
        self.assertEqual(len(unidades), 2, "a segunda passada corrigiu a primeira")

    def test_correcao_que_devolve_lixo_nao_apaga_a_primeira(self):
        """Uma segunda passada ruim não pode piorar uma primeira que estava boa."""
        respostas = iter([
            '{"assuntos":[{"inicio":0,"fim":29},{"inicio":30,"fim":59}]}',
            "não entendi o pedido",
        ])
        unidades = assuntos_por_modelo(_frases(60), lambda _: next(respostas))
        self.assertEqual(len(unidades), 2)


class FalharNuncaDerrubaAMoagem(unittest.TestCase):
    def test_modelo_que_levanta_devolve_vazio_e_avisa(self):
        avisos = []

        def explode(_):
            raise RuntimeError("sem internet")

        unidades = assuntos_por_modelo(
            _frases(60), explode, avisar=lambda t, n=None: avisos.append(t))

        self.assertEqual(unidades, [])
        self.assertTrue(any("leitura local" in a for a in avisos),
                        "vazio precisa dizer por quê")

    def test_transcricao_curta_demais_nem_pergunta(self):
        perguntou = []
        unidades = assuntos_por_modelo(
            _frases(10), lambda p: perguntou.append(p) or "{}")
        self.assertEqual(unidades, [])
        self.assertEqual(perguntou, [], "não vale gastar uma chamada em dez frases")


class OSeletorEscolheEntreOsDoisCaminhos(unittest.TestCase):
    """A ligação. Sem ela o módulo existe e ninguém o chama — que foi o que
    aconteceu com o caderninho do Acervo durante meses."""

    def _seletor(self, settings):
        from modules.clip_selector import ClipSelector

        seletor = ClipSelector.__new__(ClipSelector)
        seletor._settings_da_moagem = settings
        seletor._candidate_diagnostics = {}
        seletor.GEMINI_TIMEOUT_S = 5
        return seletor

    def test_sem_chave_usa_a_leitura_local_e_diz_isso(self):
        seletor = self._seletor({})
        unidades = seletor._assuntos_do_video(_frases(200))
        self.assertEqual(seletor._candidate_diagnostics["assuntos_origem"], "coesao_local")

    def test_com_chave_usa_o_modelo_e_diz_isso(self):
        from unittest.mock import patch

        seletor = self._seletor({"gemini_api_key": "x", "gemini_model": "gemini-2.5-flash"})
        resposta = '{"assuntos":[{"inicio":0,"fim":99},{"inicio":100,"fim":199}]}'
        with patch.object(type(seletor), "_perguntar_ao_gemini", return_value=resposta):
            unidades = seletor._assuntos_do_video(_frases(200))

        self.assertEqual(len(unidades), 2)
        self.assertEqual(seletor._candidate_diagnostics["assuntos_origem"], "modelo_por_frase")

    def test_modelo_que_falha_cai_na_leitura_local(self):
        from unittest.mock import patch

        seletor = self._seletor({"gemini_api_key": "x"})
        with patch.object(type(seletor), "_perguntar_ao_gemini",
                          side_effect=RuntimeError("429")):
            seletor._assuntos_do_video(_frases(200))

        self.assertEqual(seletor._candidate_diagnostics["assuntos_origem"], "coesao_local",
                         "quota estourada não pode deixar o vídeo sem assunto")

    def test_desligar_pelo_ajuste_e_respeitado(self):
        seletor = self._seletor({"gemini_api_key": "x", "assuntos_pelo_modelo": False})
        seletor._assuntos_do_video(_frases(200))
        self.assertEqual(seletor._candidate_diagnostics["assuntos_origem"], "coesao_local")


if __name__ == "__main__":
    unittest.main()

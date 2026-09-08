"""O corte tem que acabar quando o Renan acaba, não quando o repórter começa.

A QUEIXA DO EDITOR, EM TRÊS CORTES DA MESMA LEVA (08/09)
--------------------------------------------------------
    #17 "está bom mas deveria acabar em 1:24 que é quando o Renan acaba de
         falar, depois continua com a pergunta do próximo repórter por mais de
         30 segundos"
    #13 "o Renan para de falar aos 47-48 segundos e o vídeo continua até os 58"
    #7  "é um corte de 40 segundos e termina com uma pergunta do repórter"

Nenhum passo pegava isso. `_close_where_the_thought_ends` só SOMA material — na
moagem dele estendeu quinze cortes. `_trim_trailing_announcement` tira, mas tira
**uma frase só**, e só quando ela anuncia assunto novo por enumeração ("segundo
ponto:"). Pergunta de repórter não anuncia nada assim, e trinta segundos de
pergunta são várias frases.

Medido nas fontes com gabarito, sobre janelas de sete frases:

    sabatina_band       3 cortes terminavam no repórter -> 0    32 s removidos
    bYi5Xhrv5ps         5 cortes terminavam no repórter -> 2    54 s removidos
    inteligencia_1607   0 -> 0                                    0 s
"""

import unittest

from modules.clip_selector import ClipSelector


def _frases(linhas):
    frases, relogio = [], 0.0
    for texto, duracao in linhas:
        frases.append({"text": texto, "start": round(relogio, 3),
                       "end": round(relogio + duracao, 3)})
        relogio += duracao
    return frases


class TerminarQuandoOEntrevistadoTermina(unittest.TestCase):
    def setUp(self):
        self.seletor = ClipSelector(min_duration=15, max_duration=180, max_clips=12)

    def test_a_pergunta_do_proximo_reporter_sai_do_fim(self):
        """O caso #17: trinta segundos de pergunta pendurados no fim."""
        frases = _frases([
            ("O Brasil precisa de uma reforma na segurança pública.", 20),
            ("E é isso que o nosso plano de governo apresenta, ponto a ponto.", 22),
            ("Candidato, bom dia, Juliano do Jornal Estadão.", 8),
            ("O senhor teme novas represálias do STF após o ato de hoje?", 12),
        ])
        cortes = [{"start": 0.0, "end": 62.0, "text": "x"}]

        self.seletor._cortar_o_rabo_de_quem_pergunta(cortes, frases)

        self.assertEqual(cortes[0]["end"], 42.0,
                         "tinha que acabar onde o entrevistado para de falar")
        self.assertEqual(cortes[0]["closing_trimmed_s"], 20.0)
        self.assertIn("repórter", cortes[0]["closing_trim_reason"])

    def test_corte_que_ja_acaba_no_entrevistado_nao_e_tocado(self):
        frases = _frases([
            ("Candidato, o senhor teme represálias?", 8),
            ("Não temo, e vou explicar exatamente por quê.", 25),
            ("Porque decisão ilegal não se cumpre, e é simples assim.", 25),
        ])
        cortes = [{"start": 0.0, "end": 58.0, "text": "x"}]

        self.seletor._cortar_o_rabo_de_quem_pergunta(cortes, frases)

        self.assertEqual(cortes[0]["end"], 58.0)
        self.assertNotIn("closing_trim_reason", cortes[0])

    def test_a_pergunta_da_ABERTURA_continua_valendo(self):
        """Ele foi explícito: no COMEÇO, pergunta curta do repórter pode ficar.

        O corte mais visto de todos (9,1 M) abre com 1,5 s de pergunta. Se este
        aparo mexesse na abertura, quebraria o padrão de campeão da casa.
        """
        frases = _frases([
            ("Que Brasil que você vai pegar ano que vem?", 3),
            ("Eu vou pegar um Brasil destruído, e vou dizer por quê.", 30),
            ("Destruído pelos mesmos que se dizem donos dele.", 30),
        ])
        cortes = [{"start": 0.0, "end": 63.0, "text": "x"}]

        self.seletor._cortar_o_rabo_de_quem_pergunta(cortes, frases)

        self.assertEqual(cortes[0]["start"], 0.0, "a abertura não se mexe")
        self.assertEqual(cortes[0]["end"], 63.0)

    def test_nunca_encolhe_um_corte_ate_ele_sumir(self):
        """Corte com rabo ele apara à mão; corte que sumiu não volta."""
        frases = _frases([
            ("Não aceito essa democracia.", 10),
            ("Candidato, uma pergunta sobre o seu plano de governo?", 20),
            ("E como o senhor pretende financiar isso tudo?", 20),
        ])
        cortes = [{"start": 0.0, "end": 50.0, "text": "x"}]

        self.seletor._cortar_o_rabo_de_quem_pergunta(cortes, frases)

        self.assertEqual(cortes[0]["end"], 50.0,
                         "aparar deixaria 10 s, abaixo do mínimo; melhor deixar o rabo")

    def test_varias_frases_de_pergunta_saem_de_uma_vez(self):
        """O aparo antigo tirava UMA frase; trinta segundos são várias."""
        frases = _frases([
            ("A nossa proposta é devolver a prisão em segunda instância.", 40),
            ("Bom dia, candidato, aqui é da Jovem Pan.", 6),
            ("O senhor esteve em Fortaleza no fim de semana?", 7),
            ("E como o senhor concilia isso com o respeito às instituições?", 9),
        ])
        cortes = [{"start": 0.0, "end": 62.0, "text": "x"}]

        self.seletor._cortar_o_rabo_de_quem_pergunta(cortes, frases)

        self.assertEqual(cortes[0]["end"], 40.0, "as três frases de pergunta saem juntas")

    def test_o_aparo_esta_ligado_no_caminho_que_o_programa_usa(self):
        """Método sem chamada é método que não existe — já aconteceu aqui."""
        from pathlib import Path

        fonte = (Path(__file__).resolve().parents[1] / "modules" / "clip_selector.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("clips = self._cortar_o_rabo_de_quem_pergunta(", fonte)



class EncurtarAteFechar(unittest.TestCase):
    """A regra que ele deu em 08/09, com as palavras dele.

        "não tem problema o vídeo ter até 2 minutos mais ou menos, só é
         preferível o vídeo mais curto mesmo (...) mas o foco mesmo é muito mais
         a coerência e fechar o raciocínio do que um corte curto"

        "boa parte dos que eu rejeitei por não concluir o raciocínio eu até
         conseguiria aproveitar se eu cortasse manualmente e deixasse o corte
         menor"

    `_close_where_the_thought_ends` só sabe AVANÇAR. Quando bate no teto de
    duração, o corte termina no meio do raciocínio — foi a rejeição mais
    frequente dele, 20 de 109.

    Medido sobre janelas de onze frases nas fontes com gabarito:

        sabatina_band   10 de 32 recuados ·  95 s encurtados
        p5ZRVXBpBYk     29 de 73 recuados · 226 s encurtados
        live_ceara      11 de 31 recuados ·  67 s encurtados

    Nos candidatos da própria régua não dispara, porque ali o fecho já estava
    completo (16/16 na sabatina). O ganho aparece no material dele.
    """

    def setUp(self):
        self.seletor = ClipSelector(min_duration=15, max_duration=180, max_clips=12)

    def test_corte_que_termina_no_meio_do_raciocinio_encurta_ate_o_fecho(self):
        frases = _frases([
            ("O Brasil se tornou um país injusto com quem trabalha.", 30),
            ("E é por isso que a nossa proposta começa pela segurança.", 30),
            ("Nós vamos devolver a prisão em segunda instância.", 25),
            ("E depois disso, e ainda por cima, e além de tudo o mais.", 20),
            ("E continua falando, porque o raciocínio não acabou ali.", 20),
        ])
        # o corte para aos 105 s, no meio de uma emenda: o vídeo continua
        cortes = [{"start": 0.0, "end": 105.0, "text": "x"}]

        self.seletor._recuar_ate_o_raciocinio_fechar(cortes, frases)

        # 85 s NÃO serve: ali o corte pararia logo antes de "E depois disso",
        # que é emenda da frase anterior — o raciocínio segue aberto. O último
        # ponto onde ele fecha de verdade é 60 s, antes de "Nós vamos devolver",
        # que começa um pensamento novo.
        self.assertEqual(cortes[0]["end"], 60.0,
                         "recua até o último ponto em que o que vem depois é assunto novo")
        self.assertIn("raciocínio fecha", cortes[0]["closing_trim_reason"])

    def test_corte_que_ja_fecha_nao_e_encurtado(self):
        frases = _frases([
            ("O Brasil se tornou um país injusto com quem trabalha.", 30),
            ("Nós vamos devolver a prisão em segunda instância.", 30),
            ("Candidato, e sobre a economia?", 10),
        ])
        cortes = [{"start": 0.0, "end": 60.0, "text": "x"}]

        self.seletor._recuar_ate_o_raciocinio_fechar(cortes, frases)

        self.assertEqual(cortes[0]["end"], 60.0)
        self.assertNotIn("closing_trim_reason", cortes[0])

    def test_nunca_recua_mais_que_a_metade_do_corte(self):
        """Ele quer o raciocínio inteiro mais curto, não um pedaço dele.

        Sem esse limite, um corte de dois minutos viraria quinze segundos para
        "fechar" numa vírgula qualquer.
        """
        frases = _frases([
            ("Uma tese que se sustenta sozinha e fecha aqui mesmo.", 20),
            ("E continua, e emenda, e não para mais de falar disso.", 25),
            ("E segue emendando, e ainda continua no mesmo fôlego.", 25),
            ("E não fecha, e emenda de novo, e continua.", 25),
        ])
        cortes = [{"start": 0.0, "end": 95.0, "text": "x"}]

        self.seletor._recuar_ate_o_raciocinio_fechar(cortes, frases)

        self.assertGreaterEqual(cortes[0]["end"], 47.5,
                                "recuar até 20 s destruiria o corte para 'fechar'")

    def test_o_recuo_esta_ligado_no_caminho_que_o_programa_usa(self):
        from pathlib import Path

        fonte = (Path(__file__).resolve().parents[1] / "modules" / "clip_selector.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("clips = self._recuar_ate_o_raciocinio_fechar(", fonte)

if __name__ == "__main__":
    unittest.main()

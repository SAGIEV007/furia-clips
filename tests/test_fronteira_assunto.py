from modules.fronteira_assunto import fim_fragmentado, abre_dependente


def test_fim_fragmentado_short_fragment():
    assert fim_fragmentado("fala curta") is True
    assert fim_fragmentado("") is False
    assert fim_fragmentado("ok") is True


def test_fim_fragmentado_punctuated_sentence():
    assert fim_fragmentado("Isso é um ponto final.") is False
    assert fim_fragmentado("E com exclamação!") is False


def test_fim_fragmentado_question():
    assert fim_fragmentado("Isso é uma pergunta?") is False


def test_fim_fragmentado_backchannel_whitelist():
    assert fim_fragmentado("ta") is False
    assert fim_fragmentado("Tá") is False
    assert fim_fragmentado("uhum") is False
    assert fim_fragmentado("é isso") is False
    assert fim_fragmentado("obrigado") is False
    assert fim_fragmentado("perfeito") is False
    assert fim_fragmentado("certo") is False
    assert fim_fragmentado("exato") is False
    assert fim_fragmentado("né") is False
    assert fim_fragmentado("valeu") is False


def test_abre_dependente_short_connective():
    assert abre_dependente("E aí?") is True
    assert abre_dependente("Mas...") is True
    assert abre_dependente("Então, sim") is True


def test_abre_dependente_full_sentence():
    assert abre_dependente("O governo errou de novo.") is False
    assert abre_dependente("Ninguém aguenta mais isso.") is False


def test_abre_dependente_non_connective_start():
    assert abre_dependente("Agora vai começar.") is False


# --- Regressão: cortes reprovados pelo editor em 2026-09-03 (Flow News #065)
# Os gates recebiam o texto INTEIRO do clipe em clip_selector._editorial_flags,
# então o teto de caracteres nunca era atingido e nenhum dos dois disparava
# (0 de 86 cortes). Estes casos são o texto real dos cortes reprovados.

CORTES_REPROVADOS_ABERTURA = [
    "Ah, mas você pode atirar, mas não tem que ter letalidade. Vai que "
    "o cara morre ali e aí vira problema pra polícia toda.",
    "Tipo, danse vocês, vocês são os idiotas aí fora, vocês paguem a "
    "conta que a gente fica aqui em cima.",
    "Só só assim, só não terminei de ser democratizado por ele porque "
    "não deu tempo, mas era o plano dele.",
    "E aí a gente analisa, né, a gente vai por isso deve ser por isso "
    "que ele vai naquela cidadezinha lá.",
]


def test_abre_dependente_pega_abertura_longa_com_conectivo():
    """Abertura dependente NÃO é necessariamente curta.

    A regra de tamanho veio da pesquisa sobre o FIM do corte e foi copiada
    para a entrada sem medição. Uma frase inteira que abre em "Ah, mas..."
    depende do que veio antes, tenha ela 20 ou 200 caracteres.
    """
    for texto in CORTES_REPROVADOS_ABERTURA:
        assert abre_dependente(texto) is True, f"deveria acusar: {texto[:60]}"


def test_abre_dependente_avalia_a_primeira_frase_nao_o_clipe_todo():
    """O gate julga a janela de abertura, não o clipe inteiro."""
    # Abre bem; o "mas" no meio não pode contaminar o veredito.
    texto = (
        "O governo errou de novo. Mas ninguém aguenta mais isso, e aí a "
        "gente fica reclamando sem fazer nada."
    )
    assert abre_dependente(texto) is False


def test_fim_fragmentado_avalia_a_ultima_frase_nao_o_clipe_todo():
    """O gate julga a janela de fecho, não o clipe inteiro."""
    # Fecha em fragmento curto, mesmo com o clipe sendo longo.
    texto = "Isso é uma discussão longa sobre orçamento e responsabilidade. E aí."
    assert fim_fragmentado(texto) is True
    # Fecha completo.
    texto_ok = "Isso é uma discussão longa. O corte fecha com uma frase inteira."
    assert fim_fragmentado(texto_ok) is False

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

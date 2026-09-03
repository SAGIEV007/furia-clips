from scripts.bench_contexto import classificar_borda_saida


def test_classificar_borda_saida_ponto():
    assert classificar_borda_saida("Isso é verdade.") == "ponto_exclamacao"
    assert classificar_borda_saida("Isso é verdade!") == "ponto_exclamacao"


def test_classificar_borda_saida_pergunta():
    assert classificar_borda_saida("Isso é verdade?") == "pergunta"


def test_classificar_borda_saida_virgula():
    assert classificar_borda_saida("Isso é verdade,") == "virgula"


def test_classificar_borda_saida_sem_pontuacao():
    assert classificar_borda_saida("Isso é verdade") == "sem_pontuacao"


def test_classificar_borda_saida_com_espacos():
    assert classificar_borda_saida("Isso é verdade.  ") == "ponto_exclamacao"
    assert classificar_borda_saida("Isso é verdade?  ") == "pergunta"
    assert classificar_borda_saida("Isso é verdade,  ") == "virgula"
    assert classificar_borda_saida("Isso é verdade  ") == "sem_pontuacao"


def test_classificar_borda_saida_vazio():
    assert classificar_borda_saida("") == "sem_pontuacao"

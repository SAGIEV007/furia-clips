"""A peneira perguntava quanto o candidato REPETE. Passa a perguntar quanto ACRESCENTA.

── o que a regra antiga não distinguia ──────────────────────────────────────

    if overlap > 0.30: morre        # overlap = partilhado / menor dos dois

Medido nos 21 descartes por sobreposição da corrida real do editor (PENÉLOPE),
essa única regra matava duas coisas opostas:

    12 candidatos estavam INTEIROS dentro de um corte entregue.
       Não se perdeu nada: o corte longo contém aquela fala, e ele já disse que
       em resposta longa prefere o contexto inteiro — "aí eu mesmo edito".

     9 só encostavam na borda de outro. Um deles cobria 19:54–21:45: quase dois
       minutos que nenhum corte entregue tocou.

Os dois grupos morriam pelo mesmo motivo, e o diagnóstico dava o mesmo "1" para
cada um. A pergunta que separa não é quanto ele repete — é quanto ele acrescenta.

── o piso, medido e não achado ──────────────────────────────────────────────

O piso de proporção poderia ser qualquer número, então fui buscar um externo. Na
base do CHUB, 4.109 cortes que a campanha REALMENTE publicou nas três contas
orgânicas:

    percentil  5   facebook  32s · instagram  36s · tiktok  46s
    percentil 10   facebook  44s · instagram  48s · tiktok  60s
    mediana        facebook 102s · instagram  91s · tiktok 123s

95% de tudo que eles publicam tem 32 segundos ou mais. Foi essa medida que me
disse o que é um corte que se sustenta — e, no caminho, que ela NÃO serve como
régua de repetição (ver o teste do vazamento em test_livro_da_peneira.py: um
piso absoluto de 30s matava candidatos de 30s que só encostavam).

── a promessa que isto tem de manter ────────────────────────────────────────

"me dê certeza que isso não reduz a quantidade de cortes". Os testes de contagem
abaixo são essa certeza — e um deles cobre o caso que quase me escapou: um
candidato curto e SOZINHO, sem partilhar nada com ninguém, não pode morrer por
uma régua que existe para medir repetição.
"""

import pytest

from modules.clip_selector import ClipSelector


def _corte(inicio, fim, texto="Um trecho qualquer da entrevista.", nota=70.0):
    return {
        "start": float(inicio),
        "end": float(fim),
        "duration": float(fim - inicio),
        "text": texto,
        "viral_score": nota,
        "editorial_potential_score": nota,
        "confidence": 0.8,
    }


@pytest.fixture
def seletor():
    return ClipSelector()


# ── a conta de material inédito ────────────────────────────────────────────

def test_o_inedito_e_medido_contra_a_uniao_dos_escolhidos(seletor):
    """Par a par escondia o caso mais comum: dois vizinhos que cobrem juntos.

    Nenhum dos dois escolhidos cobre o candidato sozinho — cada um pega metade.
    Comparando de um em um, ele parecia trazer novidade contra os dois; contra a
    união dele não sobra nada.
    """
    escolhidos = [_corte(100, 150), _corte(150, 200)]
    candidato = _corte(110, 190)
    assert seletor._material_inedito(candidato, escolhidos) == pytest.approx(0.0)


def test_o_inedito_conta_so_o_que_ninguem_cobre(seletor):
    escolhidos = [_corte(100, 150)]
    candidato = _corte(120, 200)          # 30s dentro, 50s fora
    assert seletor._material_inedito(candidato, escolhidos) == pytest.approx(50.0)


def test_faixas_desordenadas_nao_confundem_a_conta(seletor):
    escolhidos = [_corte(300, 340), _corte(100, 150), _corte(200, 230)]
    candidato = _corte(90, 350)
    # 260s de candidato, cobertos: 50 + 30 + 40 = 120  →  140 inéditos
    assert seletor._material_inedito(candidato, escolhidos) == pytest.approx(140.0)


# ── o que morre e o que vive ───────────────────────────────────────────────

def test_o_engolido_inteiro_continua_morrendo(seletor):
    """Este caso não muda, e não deve mudar: é conteúdo que ele já recebeu."""
    longo = _corte(200, 343, "Resposta longa e completa sobre o tema todo.", 90.0)
    dentro = _corte(270, 310, "Um pedaço da mesma resposta.", 60.0)
    ficaram = seletor._remove_overlaps([longo, dentro])
    assert len(ficaram) == 1
    assert ficaram[0]["start"] == 200


def test_o_que_so_encosta_passa_a_sobreviver(seletor):
    """O caso real: 19:54–22:41 perdia para 21:45–24:04 e levava junto quase
    dois minutos que nenhum corte cobria.

    Pela regra antiga: partilha 57s de um menor de 139s → 0,41 > 0,30 → morria.
    Pela regra nova: acrescenta 111 dos seus 168s → 66% → vive.
    """
    vencedor = _corte(1305, 1444, "A resposta sobre o segundo assunto.", 83.0)
    perdedor = _corte(1194, 1361, "Uma fala inteira sobre outro assunto.", 83.0)
    ficaram = seletor._remove_overlaps([vencedor, perdedor])
    assert len(ficaram) == 2, (
        "o candidato que trazia quase dois minutos inéditos morreu de novo"
    )


def test_quem_repete_a_maior_parte_de_si_ainda_morre(seletor):
    """Um candidato de 165s com 51s de novidade é reler o que ele acabou de ler.

    O lead-in continua ao alcance pela ferramenta de ajustar entrada e saída —
    é justamente para isso que ela existe.
    """
    vencedor = _corte(1495, 1608, "A resposta principal, longa.", 90.0)
    perdedor = _corte(1444, 1608, "A mesma resposta com um pedaço antes.", 74.0)
    ficaram = seletor._remove_overlaps([vencedor, perdedor])
    assert len(ficaram) == 1


# ── a promessa: nada some ──────────────────────────────────────────────────

def test_um_candidato_sozinho_e_curto_nao_pode_morrer(seletor):
    """O buraco que quase entrou junto com a correção.

    A régua de material inédito existe para medir REPETIÇÃO. Um candidato de 25s
    que não encosta em ninguém não repete coisa alguma — mas um piso absoluto
    olharia só para o número e o mataria. Seria reduzir a quantidade de cortes
    por uma porta lateral.
    """
    longo = _corte(100, 300, "Uma resposta longa e completa.", 90.0)
    curto_e_sozinho = _corte(900, 925, "Uma tirada curta, noutro ponto do vídeo.", 60.0)
    ficaram = seletor._remove_overlaps([longo, curto_e_sozinho])
    assert len(ficaram) == 2, "um candidato que não encosta em ninguém desapareceu"


def test_candidatos_sem_encostar_sobrevivem_todos(seletor):
    candidatos = [_corte(i * 100, i * 100 + 60, f"Trecho {i}.", 80 - i) for i in range(8)]
    assert len(seletor._remove_overlaps(candidatos)) == 8


def test_a_peneira_nova_nunca_entrega_menos_que_a_antiga(seletor):
    """A regra nova é mais permissiva por construção — verificado, não afirmado.

    Para cada par possível de candidatos numa varredura de sobreposições, a
    contagem nova tem de ser maior ou igual à que a regra antiga daria.
    """
    def contagem_antiga(clips):
        selecionados = []
        for clip in sorted(clips, key=lambda c: -c["viral_score"]):
            if any(seletor._calculate_overlap(clip, outro) > 0.30 for outro in selecionados):
                continue
            selecionados.append(clip)
        return len(selecionados)

    for deslocamento in range(0, 100, 7):
        for duracao in (25, 40, 60, 90, 140):
            par = [
                _corte(100, 100 + duracao, "Primeira resposta.", 80.0),
                _corte(100 + deslocamento, 100 + deslocamento + duracao, "Segunda resposta.", 70.0),
            ]
            nova = len(seletor._remove_overlaps([dict(c) for c in par]))
            antiga = contagem_antiga([dict(c) for c in par])
            assert nova >= antiga, (
                f"deslocamento {deslocamento}s, duração {duracao}s: "
                f"a peneira nova entregou {nova} e a antiga entregaria {antiga}"
            )


def test_o_registro_diz_quanto_faltou_para_o_candidato_viver(seletor):
    """Sem o número, "descartado" é veredito sem apelação."""
    vencedor = _corte(200, 343, "Resposta longa.", 90.0)
    perdedor = _corte(270, 310, "Um pedaço dela.", 60.0)
    seletor._remove_overlaps([vencedor, perdedor])
    item = seletor._candidate_diagnostics["descartados_por_sobreposicao"][0]
    assert item["fracao_inedita"] == pytest.approx(0.0)
    assert item["inedito_s"] == pytest.approx(0.0)
    assert item["dentro_do_vencedor"] is True

"""Trava que impede uma proposta do acervo de engolir o destaque seguinte.

Sem ela, duas sementes vizinhas expandiam para a mesma janela: o mesmo destaque
virava duas propostas e o editor perdia um corte. Custo medido na regua do
Garimpo (02/09): acerto alto 47% -> 40% num lote de 15, cobertura parcial 73%
nos dois. Ligada mesmo assim -- destaque duplicado e defeito de produto.
"""
from modules.clip_selector import ClipSelector


def _sentencas():
    return [
        {"start": 0.0, "end": 30.0, "text": "Primeiro assunto comeca aqui e segue por um tempo.", "speaker_turn_valid": True},
        {"start": 30.0, "end": 60.0, "text": "Ainda o primeiro assunto, desenvolvendo o argumento inteiro.", "speaker_turn_valid": True},
        {"start": 60.0, "end": 90.0, "text": "Agora comeca o segundo assunto, completamente diferente do anterior.", "speaker_turn_valid": True},
        {"start": 90.0, "end": 120.0, "text": "O segundo assunto continua e fecha o raciocinio dele.", "speaker_turn_valid": True},
    ]


def _semente(inicio, fim, seed_id):
    return {
        "seed_id": seed_id,
        "start": inicio,
        "end": fim,
        "block_id": "bloco-1",
        "highlight_id": seed_id,
        "renan_speaking": True,
        "trust_tier": "qa_gated",
        "confidence": 0.9,
    }


def test_trava_ligada_por_padrao():
    assert ClipSelector.LIMITAR_EXPANSAO_ENTRE_SEMENTES is True


def test_limite_de_expansao_para_a_proposta_antes_do_proximo_destaque():
    seletor = ClipSelector(min_duration=8, max_duration=300, max_clips=5)
    proposta = seletor._build_campaign_hub_proposal(
        _sentencas(), _semente(5.0, 25.0, "h1"), limite_expansao_s=60.0
    )

    assert proposta is not None
    assert proposta["end"] <= 60.0


def test_sem_limite_a_proposta_pode_expandir_alem():
    seletor = ClipSelector(min_duration=8, max_duration=300, max_clips=5)
    com_limite = seletor._build_campaign_hub_proposal(
        _sentencas(), _semente(5.0, 25.0, "h1"), limite_expansao_s=60.0
    )
    sem_limite = seletor._build_campaign_hub_proposal(
        _sentencas(), _semente(5.0, 25.0, "h1"), limite_expansao_s=None
    )

    assert com_limite["end"] <= sem_limite["end"]


def test_limite_nao_produz_corte_abaixo_do_minimo():
    """A trava nunca pode encurtar um corte para baixo do piso publicavel."""
    seletor = ClipSelector(min_duration=45, max_duration=300, max_clips=5)
    proposta = seletor._build_campaign_hub_proposal(
        _sentencas(), _semente(5.0, 25.0, "h1"), limite_expansao_s=35.0
    )

    assert proposta is not None
    assert proposta["end"] - proposta["start"] >= 45.0

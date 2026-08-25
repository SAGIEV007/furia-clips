"""Renomear um arquivo não pode desligar o Acervo em silêncio.

Tudo o que liga o Furia ao Acervo são onze caracteres no nome do arquivo. O
editor baixa um vídeo, renomeia — que é o que qualquer pessoa faz — e a partir
dali o Furia lê a fonte sozinho como se o Acervo não tivesse nada sobre ela.
Nenhum erro, nenhum aviso: o programa simplesmente fica mais burro.

Foi exatamente o que aconteceu com o debate da Penélope. Medido:

    youtube_id_from_name("PENÉLOPE NOVA X SESTARO X REGIS TADEU… .mp4") -> None

E a mensagem que o editor via, "Nenhum bloco publicado para esta fonte", cobria
esse caso e o caso oposto — o vídeo realmente não estar no Acervo — com a mesma
frase, sem meio de distinguir um do outro.
"""

import pytest

from modules.acervo_library import (
    bind,
    bound_id_for,
    resolved_id_for,
    snapshot_path_for,
    youtube_id_from_name,
)

NOME_RENOMEADO = "PENÉLOPE NOVA X SESTARO X REGIS TADEU： O DEBATE SOBRE RENAN .mp4"


def test_o_nome_renomeado_realmente_perde_o_id():
    """O ponto de partida: o defeito existe e é este."""
    assert youtube_id_from_name(NOME_RENOMEADO) is None
    assert youtube_id_from_name("RENAN EM JOÃO PESSOA [o6yEVC-exk8].mp4") == "o6yEVC-exk8"


def test_o_vinculo_devolve_o_acervo_a_um_arquivo_renomeado(tmp_path):
    assert resolved_id_for(NOME_RENOMEADO, tmp_path) is None

    bind(NOME_RENOMEADO, "o6yEVC-exk8", tmp_path)

    assert bound_id_for(NOME_RENOMEADO, tmp_path) == "o6yEVC-exk8"
    assert resolved_id_for(NOME_RENOMEADO, tmp_path) == "o6yEVC-exk8"
    assert snapshot_path_for(f"C:/videos/{NOME_RENOMEADO}", tmp_path).name == "o6yEVC-exk8.json"


def test_o_id_no_nome_continua_valendo_mais_que_o_vinculo(tmp_path):
    """Um vínculo antigo não pode sequestrar um arquivo que já se identifica."""
    bind("RENAN EM JOÃO PESSOA [o6yEVC-exk8].mp4", "aaaaaaaaaaa", tmp_path)
    assert resolved_id_for("RENAN EM JOÃO PESSOA [o6yEVC-exk8].mp4", tmp_path) == "o6yEVC-exk8"


def test_o_vinculo_recusa_o_que_nao_e_um_id(tmp_path):
    """Um id errado gruda no arquivo e traz os blocos do vídeo de outra pessoa."""
    for valor in ("", "abc", "https://youtube.com/watch?v=o6yEVC-exk8", "id com espaço"):
        with pytest.raises(ValueError):
            bind(NOME_RENOMEADO, valor, tmp_path)
    assert resolved_id_for(NOME_RENOMEADO, tmp_path) is None


def test_o_vinculo_sobrevive_a_um_arquivo_corrompido(tmp_path):
    """O bilhete é editável à mão; um JSON quebrado não pode derrubar o corte."""
    destino = tmp_path / "acervo"
    destino.mkdir(parents=True)
    (destino / "vinculos.json").write_text("{isto não é json", encoding="utf-8")

    assert bound_id_for(NOME_RENOMEADO, tmp_path) is None
    assert resolved_id_for(NOME_RENOMEADO, tmp_path) is None

    bind(NOME_RENOMEADO, "o6yEVC-exk8", tmp_path)
    assert resolved_id_for(NOME_RENOMEADO, tmp_path) == "o6yEVC-exk8"


def test_um_caminho_inteiro_e_reduzido_ao_nome(tmp_path):
    """O vínculo segue o arquivo se ele mudar de pasta."""
    bind(f"C:/Users/nandi/Downloads/{NOME_RENOMEADO}", "o6yEVC-exk8", tmp_path)
    assert resolved_id_for(f"D:/outra/pasta/{NOME_RENOMEADO}", tmp_path) == "o6yEVC-exk8"

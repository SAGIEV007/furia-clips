"""O editor atualiza substituindo a pasta do programa inteira.

Ele perguntou se isso apaga o treinamento. A resposta é não — quem construiu
``PERSISTENT_DATA_DIR`` já tinha previsto, e o comentário no ``config.py`` diz
exatamente por quê. Mas havia uma exceção que ninguém tinha visto: os cortes
exportados nasciam em ``workspace/exports``, dentro da pasta do programa.

Isso apagava os cortes a cada atualização e, pior, apagaria junto o arquivo irmão
que carrega a origem e a decisão de cada corte — o que torna o aprendizado por
aprovação possível. ``PERSISTENT_EXPORTS_DIR`` já existia e já era criado; nada
escrevia nele.
"""

import config


def _fora_do_checkout(caminho):
    return not str(caminho).startswith(str(config.BASE_DIR))


def test_o_que_o_editor_produz_vive_fora_da_pasta_do_programa():
    for nome in (
        "PERSISTENT_DATA_DIR",
        "PERSISTENT_DATABASE_DIR",
        "PERSISTENT_PROJECTS_DIR",
        "PERSISTENT_TRANSCRIPTS_DIR",
        "PERSISTENT_DECISIONS_DIR",
        "PERSISTENT_ANALYSES_DIR",
        "PERSISTENT_BACKUPS_DIR",
    ):
        assert _fora_do_checkout(getattr(config, nome)), f"{nome} some ao atualizar"


def test_os_cortes_exportados_tambem():
    """A exceção que existia e foi corrigida."""
    assert _fora_do_checkout(config.EXPORT_DIR)
    assert config.EXPORT_DIR == config.PERSISTENT_EXPORTS_DIR


def test_o_banco_de_aprendizado_fica_fora():
    assert _fora_do_checkout(config.DB_PATH)


def test_a_pasta_de_trabalho_pode_ficar_dentro():
    """Upload e arquivo intermediário são descartáveis: nascem de novo a cada job."""
    assert not _fora_do_checkout(config.UPLOAD_DIR)

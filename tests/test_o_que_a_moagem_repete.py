"""O trabalho que a moagem fazia duas vezes — e a pasta que ela escondia.

Do registro de uma live de 56 minutos que o editor moeu:

    17:08:19  ETAPA 1/6: Lendo o silêncio da fonte
    17:08:23  58s de silêncio em 3383s de fonte (2% do material)   <- 4 segundos
    17:08:23  ETAPA 2/6: Transcrição e contexto
    17:08:23  [Gemini] Compactando cópia de análise...             <- 8 minutos
    17:16:24  Enviando...  -> HTTP 503 três vezes, desistiu
    17:21:10  Fallback local: Whisper na CPU                       <- 28 minutos
    17:50:29  [Gemini] Compactando cópia de análise...             <- 15 minutos
    18:05:21  Enviando...

A leitura do silêncio levou quatro segundos (era seis minutos e meio antes do
`-vn`). Mas a mesma cópia compactada, da mesma fonte, com os mesmos parâmetros,
foi feita DUAS VEZES na mesma rodada: uma para a transcrição e outra para a
análise editorial. Vinte e três dos cinquenta e oito minutos.

E, na mesma sessão, o botão que eu tinha acabado de pôr na barra de cima:

    POST /api/open_folder HTTP/1.1" 403
"""

import inspect
import os
import shutil
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
MOTOR = (RAIZ / "app.py").read_text(encoding="utf-8")


# ── a cópia que era refeita ─────────────────────────────────────────────────


@pytest.fixture()
def pasta_das_copias(tmp_path, monkeypatch):
    monkeypatch.setenv("FURIA_CLIPS_DATA_DIR", str(tmp_path))
    from modules import gemini_video

    pasta = gemini_video._pasta_das_copias()
    shutil.rmtree(pasta, ignore_errors=True)
    return gemini_video._pasta_das_copias()


def test_a_copia_ja_feita_e_reaproveitada(pasta_das_copias, tmp_path, monkeypatch):
    """A segunda etapa da mesma moagem não compacta de novo.

    São quinze minutos por rodada numa fonte de uma hora. O nome da cópia é
    derivado do arquivo (caminho, data, tamanho) e do perfil, então material
    diferente nunca reaproveita a cópia do outro.
    """
    from modules.gemini_video import GeminiVideoAnalyzer

    fonte = tmp_path / "fonte.mp4"
    fonte.write_bytes(b"x" * 2048)

    monkeypatch.setattr(GeminiVideoAnalyzer, "_probe_duration", staticmethod(lambda _p: 3383.0))

    # A cópia que "já tinha sido feita" na etapa anterior desta mesma moagem.
    perfil = GeminiVideoAnalyzer._proxy_profile(3383.0)
    import uuid as _uuid

    estado = fonte.stat()
    assinatura = (
        f"{fonte}|{estado.st_mtime_ns}|{estado.st_size}|"
        f"{perfil['fps']}|{perfil['max_width']}|{perfil['maxrate']}"
    )
    guardada = pasta_das_copias / (_uuid.uuid5(_uuid.NAMESPACE_URL, assinatura).hex + ".mp4")
    guardada.write_bytes(b"copia pronta")

    def nao_pode_rodar(*_a, **_k):
        raise AssertionError("compactou de novo em vez de reaproveitar a cópia pronta")

    monkeypatch.setattr("subprocess.Popen", nao_pode_rodar)

    falas = []
    caminho, ficha = GeminiVideoAnalyzer._prepare_analysis_media(
        fonte, lambda msg, nivel="info": falas.append(msg)
    )

    assert caminho == guardada
    assert ficha["reused_proxy"] is True
    assert any("reaproveitada" in f for f in falas), (
        "o console não avisou que pulou a compactação"
    )


def test_material_diferente_nao_reaproveita_a_copia_do_outro(pasta_das_copias, tmp_path, monkeypatch):
    """O nome vem do arquivo. Duas fontes diferentes nunca colidem."""
    from modules.gemini_video import GeminiVideoAnalyzer

    monkeypatch.setattr(GeminiVideoAnalyzer, "_probe_duration", staticmethod(lambda _p: 600.0))
    uma = tmp_path / "uma.mp4"
    outra = tmp_path / "outra.mp4"
    uma.write_bytes(b"a" * 100)
    outra.write_bytes(b"b" * 200)

    nomes = set()
    for fonte in (uma, outra):
        perfil = GeminiVideoAnalyzer._proxy_profile(600.0)
        import uuid as _uuid

        estado = fonte.stat()
        nomes.add(
            _uuid.uuid5(
                _uuid.NAMESPACE_URL,
                f"{fonte}|{estado.st_mtime_ns}|{estado.st_size}|"
                f"{perfil['fps']}|{perfil['max_width']}|{perfil['maxrate']}",
            ).hex
        )
    assert len(nomes) == 2, "duas fontes diferentes cairiam na mesma cópia"


def test_a_copia_guardada_nao_e_apagada_depois_de_usar():
    """Ela existe justamente para a etapa seguinte não recompactar. Apagar no
    fim da primeira análise devolveria o problema inteiro."""
    from modules.gemini_video import GeminiVideoAnalyzer

    origem = inspect.getsource(GeminiVideoAnalyzer.analyze)
    fim = origem[origem.rfind("finally:"):]
    assert "_e_copia_guardada" in fim, (
        "o fim da análise voltou a apagar a cópia guardada"
    )


def test_a_copia_so_ganha_o_nome_definitivo_quando_termina():
    """Se a máquina desligar no meio, o que fica é um temporário — e não meio
    arquivo com o nome do arquivo inteiro, que seria reaproveitado quebrado."""
    origem = inspect.getsource(
        __import__("modules.gemini_video", fromlist=["x"]).GeminiVideoAnalyzer._prepare_analysis_media
    )
    assert "proxy.replace(guardada)" in origem
    assert origem.find("returncode != 0") < origem.find("proxy.replace(guardada)"), (
        "o arquivo vira definitivo antes de saber se o ffmpeg deu certo"
    )


# ── a pasta que o botão não abria ───────────────────────────────────────────


@pytest.fixture()
def rota_da_pasta():
    corpo = MOTOR[MOTOR.find("def api_open_folder"):]
    return corpo[:corpo.find("\n@app.route")]


def test_a_pasta_de_saida_do_programa_sempre_pode_ser_aberta(rota_da_pasta):
    """`POST /api/open_folder 403` no registro dele, logo depois de eu pôr o
    botão PASTA na barra de cima.

    A lista de permitidos era `_allowed_media_roots(...) + [output_dir OU
    EXPORT_DIR]`. O "ou" significava que, escolhendo uma pasta de saída nos
    ajustes, a pasta padrão sumia da lista — e como sem caminho pedido a rota
    abria justamente a padrão, o botão respondia 403 para a única coisa que
    ele queria: ver os cortes.

    EXPORT_DIR não é entrada do usuário: é onde o programa escreve.
    """
    assert "[destino_dos_cortes, EXPORT_DIR]" in rota_da_pasta, (
        "a pasta de saída do programa voltou a poder ficar de fora dos permitidos"
    )


def test_sem_caminho_abre_onde_os_cortes_realmente_saem(rota_da_pasta):
    """Abrir a pasta padrão enquanto os cortes vão para outra é mandar ele
    procurar no lugar errado."""
    assert "destino_dos_cortes = " in rota_da_pasta
    assert 'settings.get("output_dir")' in rota_da_pasta
    trecho = rota_da_pasta[rota_da_pasta.find("if not requested:"):]
    trecho = trecho[:trecho.find("elif")]
    assert "destino_dos_cortes" in trecho


def test_a_pasta_de_fora_continua_barrada():
    """A permissão foi ampliada para uma pasta do programa, não para o disco."""
    import app as motor

    cliente = motor.app.test_client()
    for fora in ("/etc", "/root", os.path.expanduser("~")):
        resposta = cliente.post("/api/open_folder", json={"path": fora})
        assert resposta.status_code in (403, 404), (
            f"{fora} deixou de ser barrado: {resposta.status_code}"
        )

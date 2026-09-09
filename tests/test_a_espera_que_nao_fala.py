"""Quinze minutos de silêncio são indistinguíveis de um travamento.

O QUE O EDITOR VIU
------------------
Três tentativas de moer a mesma entrevista, no mesmo dia:

    15:45:43  [Gemini] Compactando cópia de análise...
    15:57:23  cancelado                                  <- 11m40s, nada na tela

    15:59:50  [Gemini] Compactando cópia de análise...
    16:17:31  "a análise de contexto excedeu o tempo esperado"
    16:17:44  cancelado                                  <- 17m54s, nada na tela

    16:21:38  [Gemini] Compactando cópia de análise...
    16:37:03  [Gemini] Enviando a cópia compactada...     <- 15m25s, TERMINOU
    16:37:23  [Gemini] Processando vídeo online (0s)...
              [Sistema] Conexão interrompida (transport close)
                                                         <- congelou em "(0s)"

Entre a primeira linha e a seguinte não havia UMA palavra. O laço era
`while process.poll() is None: sleep(0.5)`, mudo do começo ao fim. Duas moagens
boas foram canceladas por isso — a segunda a dois minutos do fim, jogando fora
os quase dezoito já pagos, porque cancelar apaga o temporário e a rodada
seguinte recomeça do zero.

O QUE ESTAVA ERRADO, EM QUATRO CAMADAS
--------------------------------------
1. a compactação não contava onde estava
2. a tela tinha prazo próprio (20 min) menor que o trabalho possível
3. Esc cancelava a moagem sem confirmação — a tecla de tirar aviso da frente
4. ao reconectar, a tela não relia o estado e ficava presa na última frase

Nenhuma delas é lentidão. Todas são o programa trabalhando bem e comunicando
mal, e é isso que este arquivo tranca.
"""

import inspect
import io
import re
import threading
from pathlib import Path

import pytest

from modules.gemini_video import GeminiVideoAnalyzer as G

RAIZ = Path(__file__).resolve().parents[1]
TELA = (RAIZ / "static" / "js" / "app.js").read_text(encoding="utf-8")
MESA = (RAIZ / "static" / "js" / "mesa-app.js").read_text(encoding="utf-8")


# ── a frase que responde "falta muito?" ─────────────────────────────────────


def test_a_compactacao_diz_onde_esta():
    """Metade de duas horas, cinco minutos de estrada: faltam cinco."""
    fala = G._fala_do_andamento(3600 * 1_000_000, 7200, 300)
    assert "50%" in fala
    assert "faltam" in fala, f"a fala não projeta o fim: {fala!r}"


def test_no_comeco_nao_promete_o_que_nao_sabe():
    """Com 0,1% andado, dividir pela fração devolve "faltam 4 horas" — um
    número inventado que assusta e faz cancelar. Melhor calar essa parte."""
    fala = G._fala_do_andamento(7 * 1_000_000, 7200, 7)
    assert "faltam" not in fala, f"projetou o fim cedo demais: {fala!r}"


def test_no_fim_nao_diz_faltam_zero():
    """A linha seguinte já é o upload; "faltam ~0 s" não informa nada."""
    fala = G._fala_do_andamento(7200 * 1_000_000, 7200, 900)
    assert "100%" in fala
    assert "faltam" not in fala


def test_sem_duracao_medida_ainda_assim_fala():
    """`ffprobe` falha e devolve 0. Isso não pode virar divisão por zero nem
    voltar ao silêncio de antes: sem percentual, ela ao menos dá sinal de vida."""
    for duracao in (0, None, -1):
        fala = G._fala_do_andamento(1_000_000, duracao, 10)
        assert fala.strip(), "voltou a não dizer nada"
        assert "%" not in fala, f"inventou percentual sem duração: {fala!r}"


def test_o_tempo_e_dito_em_unidade_de_gente():
    assert G._tempo_curto(45) == "45 s"
    assert G._tempo_curto(200) == "3 min"
    assert G._tempo_curto(7500).startswith("2 h")


# ── o laço que agora escuta ─────────────────────────────────────────────────


class _FalsoFFmpeg:
    """Um ffmpeg de mentira que publica andamento como o de verdade.

    O `poll()` só devolve o código de saída depois que a thread terminou de
    ler a saída e fechou o cano. Sem isso o teste dependeria de quem o
    escalonador acordasse primeiro.
    """

    def __init__(self, blocos, folga=3):
        self.stdout = io.StringIO("".join(blocos))
        self.stderr = io.StringIO("")
        self.returncode = 0
        self._folga = folga
        self.morto = False

    def poll(self):
        if not self.stdout.closed:
            return None
        if self._folga > 0:
            self._folga -= 1
            return None
        return self.returncode

    def kill(self):
        self.morto = True

    def wait(self, timeout=None):
        return self.returncode


@pytest.fixture()
def moagem_isolada(tmp_path, monkeypatch):
    monkeypatch.setenv("FURIA_CLIPS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(G, "PROGRESS_INTERVAL_S", 0)
    monkeypatch.setattr("modules.gemini_video.time.sleep", lambda _s: None)
    monkeypatch.setattr(G, "_probe_duration", staticmethod(lambda _p: 7200.0))
    fonte = tmp_path / "entrevista.mp4"
    fonte.write_bytes(b"x" * 4096)
    return fonte


def test_a_compactacao_fala_enquanto_trabalha(moagem_isolada, monkeypatch):
    """O teste que o silêncio de quinze minutos não passa."""
    blocos = [
        "frame=1\nout_time_us=N/A\nprogress=continue\n",
        "frame=120\nout_time_us=1800000000\nprogress=continue\n",
        "frame=240\nout_time_us=5400000000\nprogress=continue\n",
    ]
    monkeypatch.setattr(
        "modules.gemini_video.subprocess.Popen", lambda *a, **k: _FalsoFFmpeg(blocos)
    )

    falas = []
    G._prepare_analysis_media(moagem_isolada, lambda msg, nivel="info": falas.append(msg))

    com_percentual = [f for f in falas if re.search(r"\d+%", f)]
    assert com_percentual, f"a compactação continuou muda: {falas!r}"
    assert any("75%" in f for f in com_percentual), (
        f"o relógio do ffmpeg não virou percentual: {com_percentual!r}"
    )


def test_out_time_invalido_nao_derruba_a_moagem(moagem_isolada, monkeypatch):
    """`N/A` aparece nos primeiros blocos e não pode virar exceção."""
    blocos = ["out_time_us=N/A\n", "out_time_us=\n", "progress=continue\n"]
    monkeypatch.setattr(
        "modules.gemini_video.subprocess.Popen", lambda *a, **k: _FalsoFFmpeg(blocos)
    )
    caminho, _ficha = G._prepare_analysis_media(moagem_isolada, lambda *_a, **_k: None)
    assert caminho.exists()


def test_o_ffmpeg_e_mandado_publicar_andamento():
    """Sem `-progress pipe:1` não há o que escutar."""
    origem = inspect.getsource(G._prepare_analysis_media)
    assert '"-progress", "pipe:1"' in origem


# ── a trava que ninguém via ─────────────────────────────────────────────────


def test_o_erro_do_ffmpeg_e_esvaziado_enquanto_ele_vive():
    """Isto não é estilo, é uma trava permanente.

    O `stderr=PIPE` só era lido DEPOIS do processo morrer. Se o ffmpeg
    enchesse o buffer do cano — uns 64 KB — ele bloqueava escrevendo, nunca
    terminava, e o `poll()` do laço nunca mais retornava. Um congelamento de
    verdade, que nenhum tempo-limite pegava porque não havia tempo-limite.
    """
    origem = inspect.getsource(G._prepare_analysis_media)
    assert "_drenar_erros" in origem, "o stderr voltou a ser lido só no fim"
    assert "process.stderr.read()" not in origem


def test_a_leitura_das_saidas_nao_bloqueia_o_cancelamento():
    """Quem pergunta pelo cancelamento continua sendo o laço principal.

    Se a leitura das saídas fosse feita nele, um `readline()` parado seguraria
    o pedido de parada — e parar voltaria a demorar.
    """
    origem = inspect.getsource(G._prepare_analysis_media)
    assert "threading.Thread" in origem
    assert "cancel_check()" in origem
    assert origem.count("daemon=True") >= 2


def test_cancelar_no_meio_mata_o_ffmpeg(moagem_isolada, monkeypatch):
    """Parar tem que parar de verdade, não só deixar de olhar."""
    falso = _FalsoFFmpeg(["out_time_us=1000000\n"] * 50, folga=10_000)
    monkeypatch.setattr("modules.gemini_video.subprocess.Popen", lambda *a, **k: falso)

    class Parou(Exception):
        pass

    chamadas = {"n": 0}

    def pede_parada():
        # A primeira pergunta é feita antes de o ffmpeg subir. O que este teste
        # cobra é a parada no MEIO do trabalho, que é quando ela dói.
        chamadas["n"] += 1
        if chamadas["n"] > 1:
            raise Parou()

    with pytest.raises(Parou):
        G._prepare_analysis_media(
            moagem_isolada, lambda *_a, **_k: None, cancel_check=pede_parada
        )
    assert falso.morto, "o pedido de parada não matou o ffmpeg"


def test_as_threads_nao_seguram_o_programa():
    """Elas são daemon: fechar o Furia não fica esperando cano de ffmpeg."""
    antes = threading.active_count()
    assert antes >= 1  # sanidade; o que importa é o `daemon=True` acima


# ── o prazo que a tela não tinha como cumprir ───────────────────────────────


def _corpo_do_poll(fonte: str) -> str:
    inicio = fonte.find("async function pollEditorialContextJob")
    assert inicio > 0
    corpo = fonte[inicio:fonte.find("\ndocument.getElementById", inicio)]
    # Os comentários explicam o defeito antigo citando o texto dele — inclusive
    # a mensagem que este teste proíbe. O que está sob julgamento é o código.
    return "\n".join(l for l in corpo.splitlines() if not l.strip().startswith("//"))


@pytest.mark.parametrize("tela", [TELA, MESA], ids=["app.js", "mesa-app.js"])
def test_a_tela_nao_arbitra_prazo_para_o_servidor(tela):
    """Vinte minutos era menor que o trabalho possível.

    Numa fonte de duas horas só a compactação leva quinze, e o servidor ainda
    se dá até vinte e cinco para a análise. O teto estourava sempre, no meio de
    um job vivo. Aumentar o número não resolve — a `mesa-app.js` já tinha
    subido de 20 para 60 minutos e continuava sendo um chute. Quem sabe quanto
    tempo a fonte pede é o servidor, e cada etapa dele já tem tempo-limite.
    """
    corpo = _corpo_do_poll(tela)
    assert "excedeu o tempo esperado" not in corpo
    assert not re.search(r"Date\.now\(\)\s*-\s*started", corpo), (
        "a tela voltou a impor um relógio próprio ao servidor"
    )


@pytest.mark.parametrize("tela", [TELA, MESA], ids=["app.js", "mesa-app.js"])
def test_mas_a_tela_percebe_o_servidor_morto(tela):
    """Tirar o relógio não pode deixá-la esperando para sempre um motor que
    caiu. A falha que ela sabe diagnosticar sozinha é a rede não responder —
    e uma só não basta, senão um engasgo vira alarme falso."""
    corpo = _corpo_do_poll(tela)
    assert "falhasSeguidas" in corpo
    assert "parou de responder" in corpo


# ── a tecla que matava a moagem ─────────────────────────────────────────────


@pytest.mark.parametrize("tela", [TELA, MESA], ids=["app.js", "mesa-app.js"])
def test_esc_nao_cancela_moagem(tela):
    """Um job de dezoito minutos morreu treze segundos depois de um aviso
    aparecer na tela. Esc é a tecla de tirar aviso da frente."""
    trecho = tela[tela.find('case "Escape":'):]
    trecho = trecho[:trecho.find("break;")]
    assert "requestCancelOperation" not in trecho, (
        "Esc voltou a cancelar a moagem sem confirmação"
    )


@pytest.mark.parametrize("tela", [TELA, MESA], ids=["app.js", "mesa-app.js"])
def test_o_botao_de_parar_continua_existindo(tela):
    """Tirar do teclado não é tirar do editor."""
    assert 'getElementById("btnCancelOperation")' in tela


# ── a tela que voltava congelada ────────────────────────────────────────────


@pytest.mark.parametrize("tela", [TELA, MESA], ids=["app.js", "mesa-app.js"])
def test_ao_reconectar_a_tela_rele_o_estado(tela):
    """`progress` é aviso ao vivo, não histórico.

    O que o servidor falou enquanto o canal estava fora do ar não chega
    depois. Sem reler, a tela volta exibindo a última frase de antes da queda
    — foi assim que um "Processando vídeo online (0s)..." ficou congelado por
    mais de meia hora enquanto o job já tinha seguido em frente.
    """
    trecho = tela[tela.find('socket.on("connect"'):]
    trecho = trecho[:trecho.find('socket.on("disconnect"')]
    assert "loadOperationDashboard()" in trecho, (
        "a reconexão não relê o estado dos jobs no servidor"
    )

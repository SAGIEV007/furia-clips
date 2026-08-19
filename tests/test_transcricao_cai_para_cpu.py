"""A placa aceita o modelo e falha ao transcrever; isso não pode matar o trabalho.

Do log do editor, com quinze segundos entre as duas linhas:

    15:23:47  Modelo carregado: faster-whisper (int8) no CUDA; beam=1
    15:24:02  Erro na transcricao: Library cublas64_12.dll is not found

A queda para CPU existia, e existia no lugar errado: só na carga do modelo. O
ctranslate2 só abre a cuBLAS quando a inferência começa, então numa máquina com
placa presente, driver presente e runtime ausente o modelo carregava em CUDA e
morria depois, com o vídeo inteiro por transcrever e sem saída para o editor.
"""

import pytest

from modules.transcriber import Transcriber, _looks_like_a_gpu_failure


RESULTADO = {"segments": [], "segment_count": 0, "full_text": "", "language": "pt"}


def _preparado(monkeypatch, tmp_path):
    """Um transcritor já 'carregado' em CUDA, sem tocar em cache nem em ffprobe."""
    audio = tmp_path / "fonte.mp4"
    audio.write_bytes(b"nao e um mp4 de verdade, e nenhum motor real le este arquivo")

    t = Transcriber(model_name="small", language="pt")
    t.device = "cuda"
    t.compute_type = "int8"
    t._engine = "faster-whisper"
    t.model = object()

    monkeypatch.setattr(t, "_load_from_cache", lambda *a, **k: None)
    monkeypatch.setattr(t, "_save_to_cache", lambda *a, **k: None)
    monkeypatch.setattr(t, "_check_audio_stream", lambda *a, **k: True)
    monkeypatch.setattr(t, "_probe_duration", lambda *a, **k: 1863.0)
    monkeypatch.setattr(t, "_sanitize_path_for_ffmpeg", lambda p: p)
    monkeypatch.setattr(Transcriber, "_revise_captions", staticmethod(lambda *a, **k: None))
    return t, str(audio)


def test_a_mensagem_exata_do_editor_e_reconhecida_como_falha_de_placa():
    assert _looks_like_a_gpu_failure(
        RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")
    )


def test_um_erro_de_audio_nao_e_confundido_com_falha_de_placa():
    assert not _looks_like_a_gpu_failure(ValueError("O vídeo não contém stream de áudio"))
    assert not _looks_like_a_gpu_failure(FileNotFoundError("arquivo.mp4 is not found"))


def test_a_falha_da_placa_no_meio_da_transcricao_recomeca_na_cpu(monkeypatch, tmp_path):
    t, audio = _preparado(monkeypatch, tmp_path)
    tentativas = []

    def motor(*args, **kwargs):
        tentativas.append(t.device)
        if t.device == "cuda":
            raise RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")
        return dict(RESULTADO)

    def carregar(emit_progress=None):
        t.device = "cpu"
        t.compute_type = "int8"
        t.model = object()

    monkeypatch.setattr(t, "_run_engine", motor)
    monkeypatch.setattr(t, "load_model", carregar)

    resultado = t.transcribe(audio)
    assert tentativas == ["cuda", "cpu"], f"tentativas: {tentativas}"
    assert resultado["language"] == "pt"
    assert t.device == "cpu"


def test_um_erro_que_nao_e_da_placa_sobe_sem_segunda_tentativa(monkeypatch, tmp_path):
    t, audio = _preparado(monkeypatch, tmp_path)
    chamadas = []

    def motor(*args, **kwargs):
        chamadas.append(1)
        raise ValueError("áudio corrompido")

    monkeypatch.setattr(t, "_run_engine", motor)
    with pytest.raises(ValueError):
        t.transcribe(audio)
    assert len(chamadas) == 1, "um defeito de áudio não melhora na CPU; não se repete"


def test_o_cancelamento_nao_e_engolido_pela_queda_para_cpu(monkeypatch, tmp_path):
    class Cancelado(Exception):
        pass

    t, audio = _preparado(monkeypatch, tmp_path)
    chamadas = []

    def motor(*args, **kwargs):
        chamadas.append(1)
        raise Cancelado("Job cancelado pelo usuário")

    monkeypatch.setattr(t, "_run_engine", motor)
    with pytest.raises(Cancelado):
        t.transcribe(audio)
    assert len(chamadas) == 1


def test_a_queda_para_cpu_nao_deixa_o_modelo_voltar_para_a_placa(monkeypatch, tmp_path):
    """Detectar de novo escolheria CUDA de novo: placa presente, runtime ausente."""
    t, _ = _preparado(monkeypatch, tmp_path)

    def carregar_teimoso(emit_progress=None):
        t.device = "cuda"

    monkeypatch.setattr(t, "load_model", carregar_teimoso)
    with pytest.raises(RuntimeError, match="não foi respeitada"):
        t._fall_back_to_cpu()
    assert t.requested_device == "cpu", "o dispositivo tem de ficar fixado em CPU"

import os
import json
import hashlib
import time
import subprocess
import shutil
import re as _re

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace", "cache")


# Marcas de uma falha da pilha de GPU, e não do áudio nem do modelo. A biblioteca
# só é aberta de verdade quando a inferência começa, então a queda para CPU que
# existia na carga nunca chegava a valer: numa máquina com placa presente, driver
# presente e cuBLAS ausente o modelo carregava em CUDA e morria quinze segundos
# depois, com o vídeo inteiro por transcrever.
_GPU_FAILURE_MARKS = (
    "cublas", "cudnn", "cudart", "libcu", "cuda", "nvidia",
    "no kernel image", "out of memory", "device-side assert",
)


def _looks_like_a_gpu_failure(exc):
    """Whether this exception is the GPU stack failing, not the audio."""
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(mark in text for mark in _GPU_FAILURE_MARKS)


class Transcriber:
    def __init__(self, model_name="small", language="pt", word_timestamps=False, beam_size=1, device="auto"):
        self.model_name = model_name
        self.language = language
        self.word_timestamps = bool(word_timestamps)
        self.beam_size = max(1, int(beam_size or 1))
        self.requested_device = str(device or "auto").lower()
        self.device = "cpu"
        self.compute_type = "int8"
        self.model = None
        self._engine = "cache"
        os.makedirs(CACHE_DIR, exist_ok=True)

    def _detect_device(self):
        if self.requested_device in {"cpu", "cuda"}:
            return self.requested_device
        try:
            import ctranslate2
            return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except (ImportError, AttributeError, RuntimeError):
            return "cpu"

    def _get_cache_key(self, audio_path):
        stat = os.stat(audio_path)
        raw = f"{os.path.abspath(audio_path)}|{stat.st_size}|{stat.st_mtime}|{self.model_name}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _get_cache_path(self, cache_key):
        return os.path.join(CACHE_DIR, f"transcription_{cache_key}.json")

    def _load_from_cache(self, audio_path, emit_progress=None):
        cache_key = self._get_cache_key(audio_path)
        cache_path = self._get_cache_path(cache_key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if emit_progress:
                    emit_progress("Transcricao carregada do cache (instantaneo)!")
                return data
            except (json.JSONDecodeError, IOError):
                pass
        return None

    def _save_to_cache(self, audio_path, result):
        cache_key = self._get_cache_key(audio_path)
        cache_path = self._get_cache_path(cache_key)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False)
        except IOError:
            pass

    def load_model(self, emit_progress=None):
        if emit_progress:
            emit_progress(f"Carregando modelo Whisper '{self.model_name}'...")

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            if emit_progress:
                emit_progress("faster-whisper nao encontrado. Usando openai-whisper como fallback...")
            import whisper
            import torch
            # ``requested_device`` is honoured here too, otherwise a fall back to
            # CPU after a GPU failure would reload straight back onto the card.
            if self.requested_device in {"cpu", "cuda"}:
                device = self.requested_device
            else:
                device = "cuda" if torch.cuda.is_available() else "cpu"
            self.device = device
            self.compute_type = "float16" if device == "cuda" else "float32"
            self.model = whisper.load_model(self.model_name, device=device)
            self._engine = "openai-whisper"
            if emit_progress:
                emit_progress(f"Modelo carregado: openai-whisper no {device}")
            return

        detected_device = self._detect_device()
        device_candidates = [detected_device]
        if detected_device == "cuda":
            device_candidates.append("cpu")
        load_errors = []
        for device in device_candidates:
            compute_candidates = ["float16", "int8_float16", "int8"] if device == "cuda" else ["int8", "int8_float32", "float32"]
            for compute_type in compute_candidates:
                model_kwargs = {
                    "device": device,
                    "compute_type": compute_type,
                }
                if device == "cpu":
                    model_kwargs["cpu_threads"] = max(1, (os.cpu_count() or 4) - 1)
                try:
                    self.model = WhisperModel(self.model_name, **model_kwargs)
                    self.device = device
                    self.compute_type = compute_type
                    self._engine = "faster-whisper"
                    if emit_progress:
                        emit_progress(
                            f"Modelo carregado: faster-whisper ({self.compute_type}) no {self.device.upper()}; "
                            f"beam={self.beam_size}, word_timestamps={'on' if self.word_timestamps else 'off'}"
                        )
                        if detected_device == "cuda" and device == "cpu":
                            emit_progress(
                                "[Whisper] CUDA detectada, mas o backend não aceitou os tipos disponíveis; usando CPU com configuração segura.",
                                "warning",
                            )
                    return
                except (OSError, RuntimeError, ValueError) as exc:
                    load_errors.append(f"{device}/{compute_type}: {str(exc)[:160]}")

        detail = " | ".join(load_errors[-4:])
        raise RuntimeError(f"Não foi possível carregar faster-whisper com configuração segura. {detail}")

    def _probe_duration(self, video_path):
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return None
        try:
            result = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", video_path],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
            )
            return float(result.stdout.strip()) if result.stdout.strip() else None
        except (OSError, ValueError, subprocess.SubprocessError):
            return None

    def _check_audio_stream(self, video_path, emit_progress=None):
        """Check if the video file contains an audio stream. Returns True if audio exists."""
        try:
            ffprobe = shutil.which("ffprobe")
            if not ffprobe:
                return True  # Can't check, assume it has audio

            result = subprocess.run(
                [ffprobe, "-v", "quiet", "-show_streams", "-select_streams", "a", video_path],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
            )
            if "codec_type=audio" not in result.stdout:
                if emit_progress:
                    emit_progress(
                        "ERRO: Este video NAO contem audio! "
                        "Provavelmente foi baixado no formato DASH (so video). "
                        "Baixe novamente com audio incluido.",
                        "error",
                    )
                return False
            return True
        except Exception:
            return True  # Can't check, assume it has audio

    def _sanitize_path_for_ffmpeg(self, audio_path):
        """Copy file to a safe temp path if filename has special chars that break FFmpeg on Windows."""
        basename = os.path.basename(audio_path)
        if _re.search(r'[^\w\s.\-()]', basename, _re.ASCII):
            safe_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace", "cache")
            os.makedirs(safe_dir, exist_ok=True)
            ext = os.path.splitext(basename)[1]
            cache_key = self._get_cache_key(audio_path)
            safe_path = os.path.join(safe_dir, f"temp_audio_{cache_key[:16]}{ext}")
            if not os.path.exists(safe_path):
                shutil.copy2(audio_path, safe_path)
            return safe_path
        return audio_path

    def transcribe(self, audio_path, emit_progress=None, cancel_check=None):
        if cancel_check:
            cancel_check()
        cached = self._load_from_cache(audio_path, emit_progress)
        if cached:
            return cached

        # Check for audio stream before anything else
        if not self._check_audio_stream(audio_path, emit_progress):
            raise ValueError(
                "O video nao contem stream de audio. "
                "Baixe o video novamente incluindo o audio. "
                "No yt-dlp use: -f bestvideo+bestaudio --merge-output-format mp4"
            )

        duration = self._probe_duration(audio_path)
        if duration and duration >= 900 and emit_progress:
            minutes = duration / 60
            emit_progress(
                f"Fallback local: vídeo de {minutes:.1f} min; processamento CPU pode levar vários minutos. "
                "Gemini Online é recomendado para reduzir este tempo.",
                "warning",
            )

        if self.model is None:
            self.load_model(emit_progress)
        if cancel_check:
            cancel_check()

        # Handle filenames with special characters (accents, etc)
        working_path = self._sanitize_path_for_ffmpeg(audio_path)

        if emit_progress:
            emit_progress("Iniciando transcricao...")

        start_time = time.time()

        try:
            result = self._run_engine(working_path, emit_progress, cancel_check)
        except Exception as exc:
            # Cancellation and audio problems carry none of these marks and are
            # re-raised untouched.
            if self.device != "cuda" or not _looks_like_a_gpu_failure(exc):
                raise
            if emit_progress:
                emit_progress(
                    f"[Whisper] A placa aceitou o modelo mas falhou ao transcrever "
                    f"({str(exc)[:120]}). Recomeçando na CPU; vai demorar mais e vai terminar.",
                    "warning",
                )
            self._fall_back_to_cpu(emit_progress)
            result = self._run_engine(working_path, emit_progress, cancel_check)

        elapsed = time.time() - start_time
        if emit_progress:
            emit_progress(
                f"Transcricao completa: {len(result['segments'])} segmentos, "
                f"{len(result['full_text'])} caracteres ({elapsed:.0f}s)"
            )

        self._revise_captions(result, emit_progress)
        self._save_to_cache(audio_path, result)
        return result

    @staticmethod
    def _revise_captions(result, emit_progress=None):
        """Fix the names and the numbers before anything downstream reads them.

        This pass existed as a module and was wired to nothing, which is why the
        editor kept seeing "Quim Catagui" on screen after it was written: every
        clip, every caption and every headline was reading the raw recogniser
        output. It runs here, at the one point both engines pass through, so no
        later path can skip it.

        What it changes is narrow on purpose — proper nouns somebody vouched for,
        the digits that were spoken as articles, and question marks on sentences
        that are unambiguously questions. Words whose twin would change the
        meaning are counted and reported, never rewritten.
        """
        from .caption_lexicon import review_caption

        changed = 0
        to_check: list[str] = []
        for segment in result.get("segments") or []:
            verdict = review_caption(segment.get("text", ""))
            if verdict["alterado"]:
                segment["text"] = verdict["texto"]
                changed += 1
            for item in verdict["conferir"]:
                to_check.append(str(item.get("palavra") or ""))
        if changed:
            result["full_text"] = " ".join(
                str(segment.get("text") or "") for segment in result.get("segments") or []
            ).strip()
        result["revisao_legenda"] = {"linhas_corrigidas": changed, "conferir_no_audio": sorted(set(to_check))}
        if emit_progress and changed:
            aviso = f"; {len(set(to_check))} palavra(s) para conferir no áudio" if to_check else ""
            emit_progress(f"[Léxico] {changed} linha(s) corrigidas (nomes, números, interrogação){aviso}.", "info")

    def _run_engine(self, audio_path, emit_progress=None, cancel_check=None):
        if self._engine == "faster-whisper":
            return self._transcribe_faster_whisper(audio_path, emit_progress, cancel_check)
        return self._transcribe_openai_whisper(audio_path, emit_progress, cancel_check)

    def _fall_back_to_cpu(self, emit_progress=None):
        """Rebuild the model on the CPU after the GPU failed mid-transcription.

        The device is pinned rather than re-detected: detection is what chose
        CUDA in the first place, and it will choose it again — a card that is
        present and a runtime that is missing look identical to
        ``get_cuda_device_count``.
        """
        self.model = None
        self.requested_device = "cpu"
        self.device = "cpu"
        self.load_model(emit_progress)
        if self.device != "cpu":
            raise RuntimeError("A queda para CPU não foi respeitada ao recarregar o modelo.")

    def _transcribe_faster_whisper(self, audio_path, emit_progress=None, cancel_check=None):
        segments_iter, info = self.model.transcribe(
            audio_path,
            language=self.language,
            task="transcribe",
            beam_size=self.beam_size,
            word_timestamps=self.word_timestamps,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=300,
                speech_pad_ms=200,
            ),
        )

        segments = []
        full_text_parts = []

        for seg in segments_iter:
            if cancel_check:
                cancel_check()
            words = []
            if seg.words:
                for w in seg.words:
                    words.append({
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                    })

            segment_data = {
                "id": len(segments),
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
                "words": words,
            }
            segments.append(segment_data)
            full_text_parts.append(seg.text.strip())

            if emit_progress and len(segments) % 50 == 0:
                emit_progress(f"Transcrevendo... {len(segments)} segmentos processados")

        full_text = " ".join(full_text_parts)
        return {
            "segments": segments,
            "segment_count": len(segments),
            "full_text": full_text,
            "language": self.language,
        }

    def _transcribe_openai_whisper(self, audio_path, emit_progress=None, cancel_check=None):
        if cancel_check:
            cancel_check()
        # O openai-whisper usa fp16=True por padrão, mas CPU não oferece suporte
        # eficiente a esse tipo. O fallback precisa fixar fp16=False fora de CUDA.
        result = self.model.transcribe(
            audio_path,
            language=self.language,
            task="transcribe",
            verbose=False,
            word_timestamps=self.word_timestamps,
            fp16=self.device == "cuda",
        )

        segments = []
        for seg in result.get("segments", []):
            if cancel_check:
                cancel_check()
            segment_data = {
                "id": seg["id"],
                "start": round(seg["start"], 3),
                "end": round(seg["end"], 3),
                "text": seg["text"].strip(),
                "words": [],
            }
            for word_info in seg.get("words", []):
                segment_data["words"].append({
                    "word": word_info["word"].strip(),
                    "start": round(word_info["start"], 3),
                    "end": round(word_info["end"], 3),
                })
            segments.append(segment_data)

        full_text = result.get("text", "").strip()
        return {
            "segments": segments,
            "segment_count": len(segments),
            "full_text": full_text,
            "language": result.get("language", self.language),
        }

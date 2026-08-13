import os
import json
import hashlib
import time
import subprocess
import shutil
import re as _re

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace", "cache")


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
            self.device = self._detect_device()
            self.compute_type = "float16" if self.device == "cuda" else "int8"
            model_kwargs = {
                "device": self.device,
                "compute_type": self.compute_type,
            }
            if self.device == "cpu":
                model_kwargs["cpu_threads"] = max(1, (os.cpu_count() or 4) - 1)
            self.model = WhisperModel(self.model_name, **model_kwargs)
            self._engine = "faster-whisper"
            if emit_progress:
                emit_progress(
                    f"Modelo carregado: faster-whisper ({self.compute_type}) no {self.device.upper()}; "
                    f"beam={self.beam_size}, word_timestamps={'on' if self.word_timestamps else 'off'}"
                )
        except ImportError:
            if emit_progress:
                emit_progress("faster-whisper nao encontrado. Usando openai-whisper como fallback...")
            import whisper
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.device = device
            self.compute_type = "float16" if device == "cuda" else "float32"
            self.model = whisper.load_model(self.model_name, device=device)
            self._engine = "openai-whisper"
            if emit_progress:
                emit_progress(f"Modelo carregado: openai-whisper no {device}")

    def _probe_duration(self, video_path):
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return None
        try:
            result = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", video_path],
                capture_output=True, text=True, timeout=15,
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
                capture_output=True, text=True, timeout=15,
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

        if self._engine == "faster-whisper":
            result = self._transcribe_faster_whisper(working_path, emit_progress, cancel_check)
        else:
            result = self._transcribe_openai_whisper(working_path, emit_progress, cancel_check)

        elapsed = time.time() - start_time
        if emit_progress:
            emit_progress(
                f"Transcricao completa: {len(result['segments'])} segmentos, "
                f"{len(result['full_text'])} caracteres ({elapsed:.0f}s)"
            )

        self._save_to_cache(audio_path, result)
        return result

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
        result = self.model.transcribe(
            audio_path,
            language=self.language,
            task="transcribe",
            verbose=False,
            word_timestamps=self.word_timestamps,
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

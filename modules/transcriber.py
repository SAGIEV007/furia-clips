import os
import json
import hashlib
import time
import subprocess
import shutil
import re as _re

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace", "cache")


class Transcriber:
    def __init__(self, model_name="small", language="pt"):
        self.model_name = model_name
        self.language = language
        self.model = None
        self._engine = "cache"
        os.makedirs(CACHE_DIR, exist_ok=True)

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
            compute_type = "int8"
            self.model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type=compute_type,
                cpu_threads=os.cpu_count() or 4,
            )
            self._engine = "faster-whisper"
            if emit_progress:
                emit_progress(f"Modelo carregado: faster-whisper ({compute_type}) no CPU")
        except ImportError:
            if emit_progress:
                emit_progress("faster-whisper nao encontrado. Usando openai-whisper como fallback...")
            import whisper
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = whisper.load_model(self.model_name, device=device)
            self._engine = "openai-whisper"
            if emit_progress:
                emit_progress(f"Modelo carregado: openai-whisper no {device}")

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

    def transcribe(self, audio_path, emit_progress=None):
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

        if self.model is None:
            self.load_model(emit_progress)

        # Handle filenames with special characters (accents, etc)
        working_path = self._sanitize_path_for_ffmpeg(audio_path)

        if emit_progress:
            emit_progress("Iniciando transcricao...")

        start_time = time.time()

        if self._engine == "faster-whisper":
            result = self._transcribe_faster_whisper(working_path, emit_progress)
        else:
            result = self._transcribe_openai_whisper(working_path, emit_progress)

        elapsed = time.time() - start_time
        if emit_progress:
            emit_progress(
                f"Transcricao completa: {len(result['segments'])} segmentos, "
                f"{len(result['full_text'])} caracteres ({elapsed:.0f}s)"
            )

        self._save_to_cache(audio_path, result)
        return result

    def _transcribe_faster_whisper(self, audio_path, emit_progress=None):
        segments_iter, info = self.model.transcribe(
            audio_path,
            language=self.language,
            task="transcribe",
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=300,
                speech_pad_ms=200,
            ),
        )

        segments = []
        full_text_parts = []

        for seg in segments_iter:
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
            "full_text": full_text,
            "language": self.language,
        }

    def _transcribe_openai_whisper(self, audio_path, emit_progress=None):
        result = self.model.transcribe(
            audio_path,
            language=self.language,
            task="transcribe",
            verbose=False,
            word_timestamps=True,
        )

        segments = []
        for seg in result.get("segments", []):
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
            "full_text": full_text,
            "language": result.get("language", self.language),
        }

import subprocess
import json
import os
import tempfile
from config import PROCESSED_DIR


class SilenceRemover:
    def __init__(self, silence_threshold=-35, min_silence_duration=0.5, padding=0.25):
        self.silence_threshold = silence_threshold
        self.min_silence_duration = min_silence_duration
        self.padding = padding

    def detect_silence(self, video_path, emit_progress=None):
        if emit_progress:
            emit_progress("Detectando silencio no audio...")

        # `-vn` = não decodifique o vídeo.
        #
        # `silencedetect` é um filtro de ÁUDIO: a imagem não entra na conta em
        # momento nenhum. Sem esta linha o ffmpeg decodificava cada quadro de
        # vídeo da fonte inteira para depois jogar tudo fora — numa live IRL de
        # várias horas, isso é a diferença entre minutos e segundos.
        #
        # O editor mandou o registro de uma dessas: 15:28:57 começou a
        # detectar, 15:35:29 terminou. Seis minutos e meio ouvindo um áudio
        # enquanto decodificava um vídeo que ninguém ia olhar.
        cmd = [
            "ffmpeg", "-nostdin", "-hide_banner", "-i", video_path, "-vn",
            "-af", f"silencedetect=noise={self.silence_threshold}dB:d={self.min_silence_duration}",
            "-f", "null", "-"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        output = result.stderr

        silence_periods = []
        silence_start = None

        for line in output.split("\n"):
            if "silence_start:" in line:
                try:
                    silence_start = float(line.split("silence_start:")[1].strip().split()[0])
                except (ValueError, IndexError):
                    continue
            elif "silence_end:" in line and silence_start is not None:
                try:
                    parts = line.split("silence_end:")[1].strip().split()
                    silence_end = float(parts[0])
                    silence_periods.append({
                        "start": silence_start,
                        "end": silence_end,
                        "duration": round(silence_end - silence_start, 3)
                    })
                    silence_start = None
                except (ValueError, IndexError):
                    continue

        if emit_progress:
            total_silence = sum(s["duration"] for s in silence_periods)
            emit_progress(f"Encontrados {len(silence_periods)} periodos de silencio ({total_silence:.1f}s total)")

        return silence_periods

    def get_speech_segments(self, video_path, duration, emit_progress=None):
        silence_periods = self.detect_silence(video_path, emit_progress)

        if not silence_periods:
            return [{"start": 0, "end": duration}]

        speech_segments = []
        current_time = 0

        for silence in silence_periods:
            speech_start = current_time
            speech_end = silence["start"] + self.padding

            if speech_end > speech_start + 0.1:
                speech_segments.append({
                    "start": max(0, speech_start),
                    "end": min(speech_end, duration)
                })

            current_time = max(0, silence["end"] - self.padding)

        if current_time < duration - 0.1:
            speech_segments.append({
                "start": current_time,
                "end": duration
            })

        return speech_segments

    def remove_silence(self, video_path, output_path=None, emit_progress=None):
        if emit_progress:
            emit_progress("Iniciando remocao de silencio...")

        duration = self._get_duration(video_path)
        speech_segments = self.get_speech_segments(video_path, duration, emit_progress)

        if not speech_segments:
            if emit_progress:
                emit_progress("Nenhum segmento de fala encontrado.")
            return None

        if output_path is None:
            base = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(PROCESSED_DIR, f"{base}_sem_silencio.mp4")

        filter_parts = []
        for i, seg in enumerate(speech_segments):
            filter_parts.append(
                f"[0:v]trim=start={seg['start']:.3f}:end={seg['end']:.3f},setpts=PTS-STARTPTS[v{i}];"
                f"[0:a]atrim=start={seg['start']:.3f}:end={seg['end']:.3f},asetpts=PTS-STARTPTS[a{i}];"
            )

        n = len(speech_segments)
        concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(n))
        filter_complex = "".join(filter_parts) + f"{concat_inputs}concat=n={n}:v=1:a=1[outv][outa]"

        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-filter_complex", filter_complex,
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            output_path
        ]

        if emit_progress:
            emit_progress(f"Processando {n} segmentos de fala...")

        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

        if result.returncode != 0:
            if emit_progress:
                emit_progress(f"Erro no FFmpeg: {result.stderr[-500:]}")
            return None

        original_duration = duration
        new_duration = self._get_duration(output_path)
        removed = original_duration - new_duration

        if emit_progress:
            emit_progress(
                f"Silencio removido! Original: {original_duration:.1f}s -> "
                f"Novo: {new_duration:.1f}s (removidos {removed:.1f}s)"
            )

        return {
            "output_path": output_path,
            "original_duration": original_duration,
            "new_duration": new_duration,
            "removed_duration": removed,
            "segments_count": n,
        }

    def _get_duration(self, video_path):
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

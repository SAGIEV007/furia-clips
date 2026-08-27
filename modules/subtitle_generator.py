import subprocess
import os
import json
import tempfile
import unicodedata
from config import PROCESSED_DIR
from .render_presets import get_preset


SUBTITLE_RENDER_TIMEOUT_SECONDS = min(300, max(90, int(os.environ.get("FURIA_SUBTITLE_RENDER_TIMEOUT_SECONDS", "300"))))


POLITICAL_IMPACT_WORDS = {
    "absurdo", "urgente", "ilegal", "corrupcao", "stf", "moraes", "lula",
    "bolsonaro", "crime", "homicidio", "imposto", "proposta", "vitoria",
    "fracasso", "escandalo", "denuncia", "desmascarado", "brasil", "missao",
}


class SubtitleGenerator:
    def __init__(self, settings=None):
        self.settings = settings or {}
        self.font = self.settings.get("subtitle_font", "Arial")
        self.font_size = self.settings.get("subtitle_font_size", 28)
        self.text_color = self.settings.get("subtitle_color", "#FFFFFF")
        self.highlight_color = self.settings.get("subtitle_highlight_color", "#FFD700")
        self.border_color = self.settings.get("subtitle_border_color", "#000000")
        self.border_size = self.settings.get("subtitle_border_size", 1.5)
        self.highlight_size = self.settings.get("subtitle_highlight_size", 5)
        self.position = self.settings.get("subtitle_position", "bottom")
        self.style = self.settings.get("subtitle_style", "word_by_word")
        preset_name = self.settings.get("render_preset", "shorts")
        self.preset = get_preset(preset_name) if isinstance(preset_name, str) else get_preset("shorts")

    def generate_ass_file(self, segments, output_path, video_width=1080, video_height=1920):
        safe_bottom = int(self.preset.get("safe_bottom", 300))
        safe_top = int(self.preset.get("safe_top", 180))
        margin_v = safe_bottom if self.position == "bottom" else safe_top
        alignment = 2 if self.position == "bottom" else 8

        hex_text = self._color_to_ass(self.text_color)
        hex_border = self._color_to_ass(self.border_color)
        hex_highlight = self._color_to_ass(self.highlight_color)
        hex_alert = self._color_to_ass(self.settings.get("subtitle_alert_color", "#FF3B30"))

        ass_content = f"""[Script Info]
Title: Furia Clips Subtitles
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.font},{self.font_size},{hex_text},&H000000FF,{hex_border},&H00000000,-1,0,0,0,100,100,0,0,1,{self.border_size},0,{alignment},40,40,{margin_v},1
Style: Highlight,{self.font},{self.font_size},{hex_highlight},&H000000FF,{hex_border},&H00000000,-1,0,0,0,100,100,0,0,1,{self.border_size},0,{alignment},40,40,{margin_v},1
Style: Alert,{self.font},{self.font_size},{hex_alert},&H000000FF,{hex_border},&H00000000,-1,0,0,0,100,100,0,0,1,{self.border_size},0,{alignment},40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        if self.style == "word_by_word":
            # Força fonte padrão mais legível e espessa para shorts se for Arial
            if self.font == "Arial":
                ass_content = ass_content.replace(",Arial,", ",Impact,")
            ass_content += self._generate_word_by_word(segments)
        else:
            ass_content += self._generate_full_sentence(segments)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

        return output_path

    def _generate_word_by_word(self, segments):
        lines = ""
        for seg in segments:
            words = seg.get("words", [])
            if not words:
                start = self._seconds_to_ass_time(seg["start"])
                end = self._seconds_to_ass_time(seg["end"])
                lines += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{self._escape_ass_text(seg.get('text', ''))}\n"
                continue

            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = words[i:i + chunk_size]
                if not chunk:
                    continue

                chunk_start = chunk[0]["start"]
                chunk_end = chunk[-1]["end"]

                for highlight_idx in range(len(chunk)):
                    w = chunk[highlight_idx]
                    w_start = self._seconds_to_ass_time(w["start"])
                    w_end = self._seconds_to_ass_time(w["end"])

                    text_parts = []
                    for j, cw in enumerate(chunk):
                        if j == highlight_idx:
                            style_name = "Alert" if self._is_impact_word(cw.get("word", "")) else "Highlight"
                            # Pop effect: scale up slightly, then return to normal
                            pop = "{\\t(0,50,\\fscx115\\fscy115)\\t(50,150,\\fscx100\\fscy100)}"
                            text_parts.append("{\\r" + style_name + "}" + pop + self._escape_ass_text(cw.get("word", "")) + "{\\rDefault}")
                        else:
                            text_parts.append("{\\alpha&H40&}" + self._escape_ass_text(cw.get("word", "")) + "{\\alpha&H00&}")

                    line_text = " ".join(text_parts)
                    lines += f"Dialogue: 0,{w_start},{w_end},Default,,0,0,0,,{{\\fad(50,50)}}{line_text}\n"

        return lines

    def _generate_full_sentence(self, segments):
        lines = ""
        for seg in segments:
            start = self._seconds_to_ass_time(seg["start"])
            end = self._seconds_to_ass_time(seg["end"])
            text = self._escape_ass_text(seg.get("text", ""))
            lines += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n"
        return lines

    def burn_subtitles(self, video_path, ass_path, output_path=None, emit_progress=None, cancel_check=None, timeout_seconds=None):
        if output_path is None:
            base = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(PROCESSED_DIR, f"{base}_legendado.mp4")

        if emit_progress:
            emit_progress("Queimando legendas no video...")

        ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"ass={ass_escaped}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "copy",
            "-movflags", "+faststart",
            output_path
        ]

        try:
            from .video_cutter import VideoCutter

            result = VideoCutter._run_ffmpeg(
                cmd,
                cancel_check=cancel_check,
                emit_progress=emit_progress,
                progress_label="Queima de legendas",
                timeout_seconds=timeout_seconds or SUBTITLE_RENDER_TIMEOUT_SECONDS,
                heartbeat_prefix="Captions",
            )
        except Exception:
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except OSError:
                pass
            raise

        if result.returncode != 0:
            if emit_progress:
                emit_progress(f"Erro ao queimar legendas: {(result.stderr or '')[-300:]}", "error")
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except OSError:
                pass
            return None

        if emit_progress:
            emit_progress(f"Legendas queimadas com sucesso: {os.path.basename(output_path)}", "success")

        return output_path

    def generate_srt(self, segments, output_path):
        with open(output_path, "w", encoding="utf-8") as f:
            idx = 1
            for seg in segments:
                start = self._seconds_to_srt_time(seg["start"])
                end = self._seconds_to_srt_time(seg["end"])
                f.write(f"{idx}\n{start} --> {end}\n{seg['text']}\n\n")
                idx += 1
        return output_path

    def _is_impact_word(self, word):
        normalized = unicodedata.normalize("NFKD", str(word or "").lower())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        normalized = normalized.strip(".,!?;:\"'()[]{}")
        return normalized in POLITICAL_IMPACT_WORDS or any(char.isdigit() for char in normalized)

    def _escape_ass_text(self, text):
        return str(text or "").replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")

    def _color_to_ass(self, hex_color):
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"&H00{b:02X}{g:02X}{r:02X}"

    def _seconds_to_ass_time(self, seconds):
        seconds = max(0.0, float(seconds))
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def _seconds_to_srt_time(self, seconds):
        seconds = max(0.0, float(seconds))
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

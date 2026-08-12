import subprocess
import os
import json
import tempfile
import subprocess
from config import PROCESSED_DIR
from .render_presets import get_preset


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
        margin_v = 120 if self.position == "bottom" else 80
        alignment = 2 if self.position == "bottom" else 8

        hex_text = self._color_to_ass(self.text_color)
        hex_border = self._color_to_ass(self.border_color)
        hex_highlight = self._color_to_ass(self.highlight_color)

        ass_content = f"""[Script Info]
Title: Furia Clips Subtitles
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.font},{self.font_size},{hex_text},&H000000FF,{hex_border},&H80000000,1,0,0,0,100,100,0,0,1,{self.border_size},2,{alignment},40,40,{margin_v},1
Style: Highlight,{self.font},{int(self.font_size * 1.1)},{hex_highlight},&H000000FF,{hex_border},&H80000000,1,0,0,0,100,100,0,0,1,{self.border_size + 0.5},2,{alignment},40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        if self.style == "word_by_word":
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
                lines += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{seg['text']}\n"
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
                            text_parts.append("{\\rHighlight}" + self._escape_ass_text(cw.get("word", "")) + "{\\rDefault}")
                        else:
                            text_parts.append(self._escape_ass_text(cw.get("word", "")))

                    line_text = " ".join(text_parts)
                    lines += f"Dialogue: 0,{w_start},{w_end},Default,,0,0,0,,{line_text}\n"

        return lines

    def _generate_full_sentence(self, segments):
        lines = ""
        for seg in segments:
            start = self._seconds_to_ass_time(seg["start"])
            end = self._seconds_to_ass_time(seg["end"])
            text = self._escape_ass_text(seg.get("text", ""))
            lines += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n"
        return lines

    def burn_subtitles(self, video_path, ass_path, output_path=None, emit_progress=None):
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

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            if emit_progress:
                emit_progress(f"Erro ao queimar legendas: {result.stderr[-300:]}")
            return None

        if emit_progress:
            emit_progress(f"Legendas queimadas com sucesso: {os.path.basename(output_path)}")

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

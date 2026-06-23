import subprocess
import os
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter


class ThumbnailGenerator:
    def __init__(self, settings=None):
        self.settings = settings or {}
        self.width = 1280
        self.height = 720

    def extract_frame(self, video_path, time_seconds, output_path):
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(time_seconds),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return output_path if result.returncode == 0 else None

    def generate_thumbnail(self, video_path, time_seconds, text="",
                           output_path=None, style="dark_gold", emit_progress=None):
        if emit_progress:
            emit_progress("Gerando thumbnail...")

        frame_path = output_path + "_frame.jpg" if output_path else "/tmp/thumb_frame.jpg"
        self.extract_frame(video_path, time_seconds, frame_path)

        try:
            img = Image.open(frame_path)
        except Exception:
            img = Image.new("RGB", (self.width, self.height), (20, 20, 20))

        img = img.resize((self.width, self.height), Image.LANCZOS)

        if style == "dark_gold":
            img = self._apply_dark_gold_style(img, text)
        elif style == "red_impact":
            img = self._apply_red_impact_style(img, text)
        elif style == "clean_white":
            img = self._apply_clean_white_style(img, text)
        else:
            img = self._apply_dark_gold_style(img, text)

        if output_path is None:
            output_path = frame_path.replace("_frame.jpg", "_thumb.jpg")

        img.save(output_path, "JPEG", quality=95)

        try:
            os.unlink(frame_path)
        except OSError:
            pass

        if emit_progress:
            emit_progress(f"Thumbnail gerada: {os.path.basename(output_path)}")

        return output_path

    def _apply_dark_gold_style(self, img, text):
        draw = ImageDraw.Draw(img)

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        overlay_draw.rectangle(
            [(0, 0), (self.width, self.height)],
            fill=(0, 0, 0, 120)
        )

        gradient_height = self.height // 2
        for y in range(gradient_height):
            alpha = int(200 * (y / gradient_height))
            overlay_draw.rectangle(
                [(0, self.height - gradient_height + y), (self.width, self.height - gradient_height + y + 1)],
                fill=(0, 0, 0, alpha)
            )

        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay)

        if text:
            draw = ImageDraw.Draw(img)
            font = self._get_font(60)
            font_small = self._get_font(24)

            lines = self._wrap_text(text, font, self.width - 100)
            text_block = "\n".join(lines)

            y_pos = self.height - 180
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_w = bbox[2] - bbox[0]
                x_pos = (self.width - text_w) // 2

                for dx in range(-3, 4):
                    for dy in range(-3, 4):
                        draw.text((x_pos + dx, y_pos + dy), line, fill=(0, 0, 0), font=font)

                draw.text((x_pos, y_pos), line, fill=(255, 215, 0), font=font)
                y_pos += 70

            draw.text(
                (self.width - 250, 20),
                "FURIA CLIPS",
                fill=(255, 215, 0),
                font=font_small
            )

        return img.convert("RGB")

    def _apply_red_impact_style(self, img, text):
        draw = ImageDraw.Draw(img)

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(
            [(0, 0), (self.width, self.height)],
            fill=(30, 0, 0, 100)
        )
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay)

        if text:
            draw = ImageDraw.Draw(img)
            font = self._get_font(56)

            lines = self._wrap_text(text, font, self.width - 100)
            y_pos = self.height // 2 - len(lines) * 35

            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_w = bbox[2] - bbox[0]
                x_pos = (self.width - text_w) // 2

                padding = 15
                draw.rectangle(
                    [(x_pos - padding, y_pos - 5),
                     (x_pos + text_w + padding, y_pos + 65)],
                    fill=(200, 0, 0)
                )
                draw.text((x_pos, y_pos), line, fill=(255, 255, 255), font=font)
                y_pos += 75

        return img.convert("RGB")

    def _apply_clean_white_style(self, img, text):
        draw = ImageDraw.Draw(img)

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(
            [(0, self.height - 200), (self.width, self.height)],
            fill=(255, 255, 255, 230)
        )
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay)

        if text:
            draw = ImageDraw.Draw(img)
            font = self._get_font(48)
            lines = self._wrap_text(text, font, self.width - 80)
            y_pos = self.height - 180

            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_w = bbox[2] - bbox[0]
                x_pos = (self.width - text_w) // 2
                draw.text((x_pos, y_pos), line, fill=(30, 30, 30), font=font)
                y_pos += 55

        return img.convert("RGB")

    def _get_font(self, size):
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/impact.ttf",
        ]
        for path in font_paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    def _wrap_text(self, text, font, max_width):
        words = text.split()
        lines = []
        current_line = ""

        dummy_img = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(dummy_img)

        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines[:3]

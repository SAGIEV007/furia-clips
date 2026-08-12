import json
import os
import re
import unicodedata
import subprocess
from config import EXPORT_DIR
from .media_validation import validate_media
from .render_presets import get_preset, ffmpeg_video_filter


class VideoCutter:
    def __init__(self, method="intelligent", target_duration=45, preset="shorts"):
        self.method = method
        self.target_duration = target_duration
        self.preset = get_preset(preset) if isinstance(preset, str) else (preset or get_preset("shorts"))

    def get_video_info(self, video_path):
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)

    def detect_scenes(self, video_path, threshold=27.0, emit_progress=None):
        if emit_progress:
            emit_progress("Detectando mudancas de cena...")

        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"select='gt(scene,{threshold / 100.0})',showinfo",
            "-f", "null", "-"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        scene_changes = [0.0]
        for line in result.stderr.split("\n"):
            if "pts_time:" in line:
                try:
                    time_str = line.split("pts_time:")[1].split()[0]
                    scene_changes.append(float(time_str))
                except (ValueError, IndexError):
                    continue

        if emit_progress:
            emit_progress(f"Detectadas {len(scene_changes)} mudancas de cena")

        return sorted(set(scene_changes))

    def find_smart_cuts(self, transcription_segments, energy_profile=None,
                        scene_changes=None, emit_progress=None):
        if emit_progress:
            emit_progress("Calculando cortes inteligentes...")

        if not transcription_segments:
            return []

        min_dur = max(15, self.target_duration - 15)
        max_dur = self.target_duration + 15

        candidates = []
        n_segments = len(transcription_segments)

        for i in range(n_segments):
            seg_start = transcription_segments[i]["start"]
            accumulated_text = ""
            seg_end = seg_start

            for j in range(i, n_segments):
                seg_end = transcription_segments[j]["end"]
                accumulated_text += " " + transcription_segments[j]["text"]
                duration = seg_end - seg_start

                if duration < min_dur:
                    continue
                if duration > max_dur:
                    break

                candidate = {
                    "start": seg_start,
                    "end": seg_end,
                    "duration": round(duration, 3),
                    "text": accumulated_text.strip(),
                    "start_segment": i,
                    "end_segment": j,
                }
                candidates.append(candidate)

        if emit_progress:
            emit_progress(f"Encontrados {len(candidates)} candidatos a corte")

        return candidates

    def cut_clip(self, video_path, start_time, end_time, output_path,
                 vertical=True, emit_progress=None, video_layout=None, preset=None):
        if emit_progress:
            emit_progress(f"Cortando clip {start_time:.1f}s - {end_time:.1f}s...")

        duration = end_time - start_time

        active_preset = preset or self.preset
        vf_str = ffmpeg_video_filter(active_preset, layout=video_layout or "center") if vertical else None

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-i", video_path,
            "-t", str(duration),
        ]

        if vf_str:
            cmd.extend(["-vf", vf_str])

        cmd.extend([
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output_path
        ])

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            if emit_progress:
                emit_progress(f"Erro ao cortar: {result.stderr[-300:]}")
            return None

        if emit_progress:
            emit_progress(f"Clip criado: {os.path.basename(output_path)}")

        return output_path

    def cut_clip_with_face_tracking(self, video_path, start_time, end_time,
                                     output_path, face_positions=None, emit_progress=None, preset=None):
        if emit_progress:
            emit_progress(f"Cortando clip com face tracking {start_time:.1f}s - {end_time:.1f}s...")

        duration = end_time - start_time

        info = self.get_video_info(video_path)
        video_stream = next(
            (s for s in info.get("streams", []) if s["codec_type"] == "video"), None
        )
        if not video_stream:
            return self.cut_clip(video_path, start_time, end_time, output_path, True, emit_progress)

        orig_w = int(video_stream["width"])
        orig_h = int(video_stream["height"])
        crop_w = int(orig_h * 9 / 16)

        if face_positions and len(face_positions) > 0:
            avg_x = sum(fp.get("center_x", 0.5) for fp in face_positions) / len(face_positions)
            crop_x = int(avg_x * orig_w - crop_w / 2)
            crop_x = max(0, min(crop_x, orig_w - crop_w))
        else:
            crop_x = (orig_w - crop_w) // 2

        active_preset = preset or self.preset
        vf = f"crop={crop_w}:{orig_h}:{crop_x}:0,scale={active_preset['width']}:{active_preset['height']}"

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-i", video_path,
            "-t", str(duration),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            if emit_progress:
                emit_progress(f"Erro ao cortar com face tracking: {result.stderr[-300:]}")
            return self.cut_clip(video_path, start_time, end_time, output_path, True, emit_progress)

        if emit_progress:
            emit_progress(f"Clip com face tracking criado: {os.path.basename(output_path)}")

        return output_path

    def _sanitize_folder_name(self, name, max_len=80):
        """Create a safe folder name from video title."""
        safe = re.sub(r'[<>:"/\\|?*]', '', name)
        safe = safe.strip('. ')
        if len(safe) > max_len:
            safe = safe[:max_len].rstrip('. ')
        return safe or "clips"

    def _sanitize_filename(self, name, max_len=60):
        """Create a safe filename from clip title."""
        safe = re.sub(r'[<>:"/\\|?*\n\r]', '', name)
        safe = safe.strip('. ')
        if len(safe) > max_len:
            safe = safe[:max_len].rstrip('. ')
        return safe or "clip"

    def batch_cut(self, video_path, cuts, project_name, use_face_tracking=False,
                  face_positions_map=None, emit_progress=None, output_dir=None,
                  video_layout=None, preset=None):
        active_preset = get_preset(preset) if isinstance(preset, str) else (preset or self.preset)
        base_export = output_dir if output_dir and os.path.isabs(output_dir) else EXPORT_DIR

        # Create subfolder named after the video
        folder_name = self._sanitize_folder_name(project_name)
        export_dir = os.path.join(base_export, folder_name)
        os.makedirs(export_dir, exist_ok=True)

        # For debates, use centered crop instead of face tracking
        if video_layout == "debate":
            use_face_tracking = False
            if emit_progress:
                emit_progress("[Layout] Debate detectado. Usando enquadramento centralizado.", "info")

        results = []

        for i, cut in enumerate(cuts):
            rank = i + 1
            # Use AI-generated title if available, otherwise generate from text
            clip_title = cut.get("title", "")
            if not clip_title:
                clip_title = self._generate_clip_title(cut.get("text", ""))

            safe_title = self._sanitize_filename(clip_title)
            output_name = f"{rank}. {safe_title}.mp4"
            output_path = os.path.join(export_dir, output_name)

            if emit_progress:
                emit_progress(f"Cortando clip {rank}/{len(cuts)}: {safe_title}...")

            # Apply padding for natural-sounding clips
            # +0.3s before (smooth start), +0.8s after (don't cut last word)
            padded_start = max(0, cut["start"] - 0.3)
            padded_end = cut["end"] + 0.8

            if use_face_tracking and face_positions_map:
                face_pos = face_positions_map.get(i, None)
                result = self.cut_clip_with_face_tracking(
                    video_path, padded_start, padded_end,
                    output_path, face_pos, emit_progress, active_preset
                )
            else:
                result = self.cut_clip(
                    video_path, padded_start, padded_end,
                    output_path, vertical=True, emit_progress=emit_progress,
                    video_layout=video_layout, preset=active_preset
                )

            if result:
                validation = validate_media(
                    result,
                    expected_width=active_preset["width"],
                    expected_height=active_preset["height"],
                    expected_duration=max(0.1, padded_end - padded_start),
                    duration_tolerance=2.0,
                    require_audio=True,
                    require_video=True,
                )
                if not validation.valid:
                    if emit_progress:
                        emit_progress(
                            f"Validação falhou para {os.path.basename(result)}: "
                            + "; ".join(validation.errors),
                            "error",
                        )
                    continue
                results.append({
                    "index": i,
                    "path": output_path,
                    "start": cut["start"],
                    "end": cut["end"],
                    "duration": cut["duration"],
                    "text": cut.get("text", ""),
                    "title": clip_title,
                    "rank": rank,
                    "output_folder": export_dir,
                    "validation": validation.as_dict(),
                    "preset": active_preset["aspect"],
                })

        if emit_progress:
            emit_progress(f"Corte completo: {len(results)}/{len(cuts)} clips gerados")
            emit_progress(f"Clips salvos em: {export_dir}", "success")

        return results

    def _generate_clip_title(self, text):
        """Generate a title from clip text if no AI title is available."""
        if not text:
            return "Clip sem titulo"
        # Get first sentence
        for end_char in ["!", "?", "."]:
            idx = text.find(end_char)
            if 10 < idx < 80:
                return text[:idx + 1].strip()
        # Fallback: first ~50 chars at word boundary
        words = text.split()[:8]
        title = " ".join(words)
        if len(title) > 60:
            title = title[:57] + "..."
        return title

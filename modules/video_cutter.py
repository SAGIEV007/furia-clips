import subprocess
import json
import os
import re
from config import EXPORT_DIR


class VideoCutter:
    def __init__(self, method="intelligent", target_duration=45):
        self.method = method
        self.target_duration = target_duration

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
                 vertical=True, emit_progress=None):
        if emit_progress:
            emit_progress(f"Cortando clip {start_time:.1f}s - {end_time:.1f}s...")

        duration = end_time - start_time

        vf_filters = []
        if vertical:
            vf_filters.append("crop=ih*9/16:ih")
            vf_filters.append("scale=1080:1920")

        vf_str = ",".join(vf_filters) if vf_filters else None

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
                                     output_path, face_positions=None, emit_progress=None):
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

        vf = f"crop={crop_w}:{orig_h}:{crop_x}:0,scale=1080:1920"

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

    def batch_cut(self, video_path, cuts, project_name, use_face_tracking=False,
                  face_positions_map=None, emit_progress=None):
        os.makedirs(EXPORT_DIR, exist_ok=True)
        results = []

        for i, cut in enumerate(cuts):
            output_name = f"{project_name}_clip_{i+1:03d}.mp4"
            output_path = os.path.join(EXPORT_DIR, output_name)

            if emit_progress:
                emit_progress(f"Cortando clip {i+1}/{len(cuts)}...")

            if use_face_tracking and face_positions_map:
                face_pos = face_positions_map.get(i, None)
                result = self.cut_clip_with_face_tracking(
                    video_path, cut["start"], cut["end"],
                    output_path, face_pos, emit_progress
                )
            else:
                result = self.cut_clip(
                    video_path, cut["start"], cut["end"],
                    output_path, vertical=True, emit_progress=emit_progress
                )

            if result:
                results.append({
                    "index": i,
                    "path": output_path,
                    "start": cut["start"],
                    "end": cut["end"],
                    "duration": cut["duration"],
                    "text": cut.get("text", ""),
                })

        if emit_progress:
            emit_progress(f"Corte completo: {len(results)}/{len(cuts)} clips gerados")

        return results

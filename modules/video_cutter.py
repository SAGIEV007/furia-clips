import json
import os
import re
import unicodedata
import subprocess
import math
import time
import hashlib
from functools import lru_cache
from config import EXPORT_DIR
from .media_validation import validate_media
from .render_presets import get_preset, ffmpeg_video_filter


class VideoCutter:
    def __init__(self, method="intelligent", target_duration=45, preset="shorts"):
        self.method = method
        self.target_duration = target_duration
        self.preset = get_preset(preset) if isinstance(preset, str) else (preset or get_preset("shorts"))
        self.last_rejections = []
        self._ffprobe_cache = {}

    def _record_render_rejection(self, output_path, errors, warnings=None):
        self.last_rejections.append({
            "path": output_path,
            "errors": [str(error)[:500] for error in (errors or [])],
            "warnings": [str(warning)[:500] for warning in (warnings or [])],
        })

    def _validate_rendered_output(
        self,
        output_path,
        expected_duration,
        emit_progress=None,
        preset=None,
        validate_dimensions=True,
    ):
        active_preset = preset if preset is not None else self.preset
        validation = validate_media(
            output_path,
            expected_duration=max(0.1, float(expected_duration or 0)),
            duration_tolerance=2.0,
            expected_width=(
                int(active_preset.get("width"))
                if validate_dimensions and isinstance(active_preset, dict) and active_preset.get("width")
                else None
            ),
            expected_height=(
                int(active_preset.get("height"))
                if validate_dimensions and isinstance(active_preset, dict) and active_preset.get("height")
                else None
            ),
            require_audio=True,
            require_video=True,
        )
        if validation.valid:
            return True
        self._record_render_rejection(output_path, validation.errors, validation.warnings)
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except OSError:
            pass
        if emit_progress:
            emit_progress(
                f"Renderização rejeitada para {os.path.basename(output_path)}: "
                + "; ".join(validation.errors),
                "error",
            )
        return False

    def _ffprobe_cache_key(self, video_path):
        try:
            st = os.stat(video_path)
            return hashlib.sha256(f"{video_path}:{st.st_size}:{st.st_mtime_ns}".encode()).hexdigest()
        except OSError:
            return video_path

    def get_video_info(self, video_path):
        cache_key = self._ffprobe_cache_key(video_path)
        if cache_key in self._ffprobe_cache:
            return self._ffprobe_cache[cache_key]

        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            raise RuntimeError((result.stderr or "ffprobe falhou").strip()[-500:])

        info = json.loads(result.stdout or "{}")
        self._ffprobe_cache[cache_key] = info
        return info

    def clear_ffprobe_cache(self):
        """Drop cached probe results. Call after renders that replace files."""
        self._ffprobe_cache.clear()

    def detect_scenes(self, video_path, threshold=27.0, emit_progress=None):
        if emit_progress:
            emit_progress("Detectando mudancas de cena...")

        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"select='gt(scene,{threshold / 100.0})',showinfo",
            "-f", "null", "-"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

        scene_changes = [0.0]
        stderr = result.stderr or ""
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        for line in str(stderr).split("\n"):
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

    @staticmethod
    def _run_ffmpeg(cmd, output_path, cancel_check=None):
        if cancel_check is None:
            return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        cancel_check()
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            while process.poll() is None:
                cancel_check()
                time.sleep(0.2)
            stdout, stderr = process.communicate()
            return subprocess.CompletedProcess(
                cmd,
                process.returncode,
                stdout=stdout or "",
                stderr=stderr or "",
            )
        except Exception:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except OSError:
                pass
            raise

    def cut_clip(self, video_path, start_time, end_time, output_path,
                 vertical=True, emit_progress=None, video_layout=None, preset=None,
                 cancel_check=None):
        if emit_progress:
            emit_progress(f"Cortando clip {start_time:.1f}s - {end_time:.1f}s...")

        try:
            start_time = float(start_time)
            end_time = float(end_time)
        except (TypeError, ValueError):
            start_time = end_time = float("nan")
        duration = end_time - start_time
        if not all(math.isfinite(value) for value in (start_time, end_time, duration)) or duration <= 0:
            if emit_progress:
                emit_progress("[Render] Limites inválidos; clip ignorado.", "warning")
            return None

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

        result = self._run_ffmpeg(cmd, output_path, cancel_check=cancel_check)

        if result.returncode != 0:
            error_detail = (result.stderr or result.stdout or "FFmpeg encerrou com erro").strip()[-500:]
            self._record_render_rejection(output_path, [f"FFmpeg: {error_detail}"])
            if emit_progress:
                emit_progress(f"Erro ao cortar: {error_detail}", "error")
            return None

        if not self._validate_rendered_output(
            output_path,
            duration,
            emit_progress,
            preset=active_preset,
            validate_dimensions=vertical,
        ):
            return None

        if emit_progress:
            emit_progress(f"Clip criado: {os.path.basename(output_path)}")

        return output_path

    def _sanitize_face_positions(self, face_positions, emit_progress=None):
        """Keep only finite positive-confidence points and clamp coordinates."""
        if not isinstance(face_positions, (list, tuple)):
            return []
        sanitized = []
        discarded = 0
        for point in face_positions:
            if not isinstance(point, dict):
                discarded += 1
                continue
            try:
                center_x = float(point.get("center_x", 0.5))
                center_y = float(point.get("center_y", 0.5))
                confidence = float(point.get("confidence", 0))
            except (TypeError, ValueError):
                discarded += 1
                continue
            if not all(math.isfinite(value) for value in (center_x, center_y, confidence)) or confidence <= 0:
                discarded += 1
                continue
            sanitized.append({
                "center_x": max(0.0, min(1.0, center_x)),
                "center_y": max(0.0, min(1.0, center_y)),
                "confidence": max(0.0001, min(1.0, confidence)),
            })
        if discarded and emit_progress:
            emit_progress(
                f"[Layout] {discarded} sinal(is) facial(is) inválido(s) descartado(s); crop seguro será preservado.",
                "warning",
            )
        if not sanitized and face_positions and emit_progress:
            emit_progress(
                "[Layout] Nenhum sinal facial confiável sobrou; usando enquadramento centralizado.",
                "warning",
            )
        return sanitized

    def cut_clip_with_face_tracking(self, video_path, start_time, end_time,
                                     output_path, face_positions=None, emit_progress=None, preset=None,
                                     cancel_check=None):
        if emit_progress:
            emit_progress(f"Cortando clip com face tracking {start_time:.1f}s - {end_time:.1f}s...")

        try:
            start_time = float(start_time)
            end_time = float(end_time)
        except (TypeError, ValueError):
            start_time = end_time = float("nan")
        duration = end_time - start_time
        if not all(math.isfinite(value) for value in (start_time, end_time, duration)) or duration <= 0:
            if emit_progress:
                emit_progress("[Render] Limites inválidos para face tracking; clip ignorado.", "warning")
            return None

        active_preset = preset or self.preset
        try:
            info = self.get_video_info(video_path)
        except Exception as exc:
            if emit_progress:
                emit_progress(
                    f"Face tracking indisponível; usando corte convencional: {str(exc)[:240]}",
                    "warning",
                )
            return self.cut_clip(
                video_path,
                start_time,
                end_time,
                output_path,
                vertical=True,
                emit_progress=emit_progress,
                preset=active_preset,
                cancel_check=cancel_check,
            )
        video_stream = next(
            (s for s in info.get("streams", []) if s["codec_type"] == "video"), None
        )
        if not video_stream:
            return self.cut_clip(
                video_path,
                start_time,
                end_time,
                output_path,
                vertical=True,
                emit_progress=emit_progress,
                preset=active_preset,
                cancel_check=cancel_check,
            )

        orig_w = int(video_stream["width"])
        orig_h = int(video_stream["height"])
        target_w = int(active_preset["width"])
        target_h = int(active_preset["height"])
        target_aspect = target_w / max(target_h, 1)
        source_aspect = orig_w / max(orig_h, 1)

        if source_aspect >= target_aspect:
            crop_h = orig_h
            crop_w = min(orig_w, max(2, int(round(crop_h * target_aspect))))
        else:
            crop_w = orig_w
            crop_h = min(orig_h, max(2, int(round(crop_w / target_aspect))))

        safe_face_positions = self._sanitize_face_positions(face_positions, emit_progress=emit_progress)
        weights = [point["confidence"] for point in safe_face_positions]
        if weights:
            total_weight = sum(weights)
            avg_x = sum(point["center_x"] * weight for point, weight in zip(safe_face_positions, weights)) / total_weight
            avg_y = sum(point["center_y"] * weight for point, weight in zip(safe_face_positions, weights)) / total_weight
        else:
            avg_x = avg_y = 0.5
        crop_x = int(avg_x * orig_w - crop_w / 2)
        crop_y = int(avg_y * orig_h - crop_h / 2)
        crop_x = max(0, min(crop_x, orig_w - crop_w))
        crop_y = max(0, min(crop_y, orig_h - crop_h))

        vf = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={target_w}:{target_h}"

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

        result = self._run_ffmpeg(cmd, output_path, cancel_check=cancel_check)

        if result.returncode != 0:
            if emit_progress:
                emit_progress(f"Erro ao cortar com face tracking: {result.stderr[-300:]}")
            return self.cut_clip(
                video_path, start_time, end_time, output_path, vertical=True,
                emit_progress=emit_progress, preset=active_preset, cancel_check=cancel_check,
            )

        if not self._validate_rendered_output(output_path, duration, emit_progress, preset=active_preset):
            return None

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
                  video_layout=None, preset=None, original_aspect_indices=None,
                  layout_plans=None, source_duration=None, cancel_check=None):
        active_preset = get_preset(preset) if isinstance(preset, str) else (preset or self.preset)
        self.last_rejections = []
        base_export = output_dir if output_dir and os.path.isabs(output_dir) else EXPORT_DIR

        # Create subfolder named after the video
        folder_name = self._sanitize_folder_name(project_name)
        export_dir = os.path.join(base_export, folder_name)
        os.makedirs(export_dir, exist_ok=True)

        original_aspect_indices = set(original_aspect_indices or [])
        if video_layout in {"debate", "unknown", "fullscreen"}:
            original_aspect_indices.update(range(len(cuts)))
            use_face_tracking = False
            if emit_progress:
                emit_progress("[Layout] Locutor não identificado com segurança. Preservando o enquadramento original 16:9.", "info")

        results = []
        try:
            source_duration = float(source_duration) if source_duration is not None else None
        except (TypeError, ValueError):
            source_duration = None
        if source_duration is not None and (not math.isfinite(source_duration) or source_duration <= 0):
            source_duration = None

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

            # Apply padding for natural-sounding clips only after validating the
            # candidate itself. Padding must never rescue an invalid interval.
            try:
                raw_start = float(cut["start"])
                raw_end = float(cut["end"])
            except (KeyError, TypeError, ValueError):
                raw_start = raw_end = 0.0
            if (
                not all(math.isfinite(value) for value in (raw_start, raw_end))
                or raw_start < 0
                or raw_end <= raw_start
            ):
                self._record_render_rejection(output_path, ["limites de intervalo inválidos"])
                if emit_progress:
                    emit_progress(
                        f"[Render] Intervalo {rank} possui limites inválidos; ignorado.",
                        "warning",
                    )
                continue

            # Word-timestamp refinement already includes a conservative 120 ms
            # speech margin. Do not add the legacy padding again, otherwise the
            # final render would partially undo the selector's boundary work.
            boundary_refinement = cut.get("boundary_refinement") if isinstance(cut.get("boundary_refinement"), dict) else {}
            refined_boundaries = boundary_refinement.get("applied") is True
            if refined_boundaries:
                padded_start = raw_start
                padded_end = raw_end
                render_boundary_policy = "word_timestamps_preserved"
            else:
                # Legacy candidates keep the historical safety padding.
                padded_start = max(0.0, raw_start - 0.3)
                padded_end = raw_end + 0.8
                render_boundary_policy = "legacy_safety_padding"
            if source_duration is not None:
                padded_start = min(padded_start, max(0.0, source_duration - 0.1))
                padded_end = min(padded_end, source_duration)
            if padded_end <= padded_start:
                self._record_render_rejection(output_path, ["duração não positiva após limitar à fonte"])
                if emit_progress:
                    emit_progress(
                        f"[Render] Intervalo {rank} não possui duração positiva após limitar à fonte; ignorado.",
                        "warning",
                    )
                continue

            layout_plan = layout_plans.get(i) if isinstance(layout_plans, dict) else None
            if layout_plan and (
                layout_plan.get("reframe_allowed") is False
                or layout_plan.get("review_required") is True
            ):
                original_aspect_indices.add(i)

            face_pos = face_positions_map.get(i, None) if face_positions_map else None
            can_reframe = use_face_tracking and bool(face_pos) and i not in original_aspect_indices
            framing_reason = ""
            if can_reframe:
                result = self.cut_clip_with_face_tracking(
                    video_path, padded_start, padded_end,
                    output_path, face_pos, emit_progress, active_preset,
                    cancel_check=cancel_check,
                )
                framing_mode = "face_tracking"
                framing_reason = "facetracking aplicado com posição facial detectada"
            elif i in original_aspect_indices:
                result = self.cut_clip(
                    video_path, padded_start, padded_end,
                    output_path, vertical=False, emit_progress=emit_progress,
                    video_layout="center", preset=active_preset,
                    cancel_check=cancel_check,
                )
                framing_mode = "original_16_9"
                framing_reason = (layout_plan or {}).get("reason") or "composição original preservada por segurança"
                if emit_progress:
                    emit_progress(f"[Layout] Clip {rank}: {framing_reason} Saída na proporção original.", "info")
            else:
                result = self.cut_clip(
                    video_path, padded_start, padded_end,
                    output_path, vertical=True, emit_progress=emit_progress,
                    video_layout=video_layout, preset=active_preset,
                    cancel_check=cancel_check,
                )
                framing_mode = "center_crop"
                framing_reason = "crop centralizado; facetracking não aplicado ou não disponível"

            if cancel_check:
                cancel_check()
            if result:
                render_vertical = framing_mode != "original_16_9"
                validation = validate_media(
                    result,
                    expected_width=active_preset["width"] if render_vertical else None,
                    expected_height=active_preset["height"] if render_vertical else None,
                    expected_duration=max(0.1, padded_end - padded_start),
                    duration_tolerance=2.0,
                    require_audio=True,
                    require_video=True,
                )
                if not validation.valid:
                    self._record_render_rejection(result, validation.errors, validation.warnings)
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
                    "render_start": round(padded_start, 3),
                    "render_end": round(padded_end, 3),
                    "render_duration": round(padded_end - padded_start, 3),
                    "render_boundary_policy": render_boundary_policy,
                    "boundary_refinement": dict(boundary_refinement) if boundary_refinement else None,
                    "scene_boundary_adjustment": (
                        dict(cut.get("scene_boundary_adjustment"))
                        if isinstance(cut.get("scene_boundary_adjustment"), dict)
                        else None
                    ),
                    "text": cut.get("text", ""),
                    "title": clip_title,
                    "rank": rank,
                    "output_folder": export_dir,
                    "framing_mode": framing_mode,
                    "framing_reason": framing_reason,
                    "framing_confidence": (layout_plan or {}).get("confidence") if framing_mode in {"face_tracking", "original_16_9"} else None,
                    "validation": validation.as_dict(),
                    "preset": active_preset["aspect"] if render_vertical else "original_16:9",
                    "layout_plan": dict(layout_plan) if isinstance(layout_plan, dict) else None,
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

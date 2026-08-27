import json
import os
import re
import unicodedata
import subprocess
import time
from config import EXPORT_DIR


SCENE_DETECTION_TIMEOUT_SECONDS = max(
    10,
    int(os.environ.get("FURIA_SCENE_DETECTION_TIMEOUT_SECONDS", "120")),
)
RENDER_TIMEOUT_MIN_SECONDS = max(60, int(os.environ.get("FURIA_RENDER_TIMEOUT_MIN_SECONDS", "180")))
RENDER_TIMEOUT_MAX_SECONDS = max(RENDER_TIMEOUT_MIN_SECONDS, int(os.environ.get("FURIA_RENDER_TIMEOUT_MAX_SECONDS", "900")))
RENDER_HEARTBEAT_SECONDS = max(5, int(os.environ.get("FURIA_RENDER_HEARTBEAT_SECONDS", "15")))
from .media_validation import validate_media
from .render_presets import get_preset, ffmpeg_video_filter


class VideoCutter:
    def __init__(self, method="intelligent", target_duration=45, preset="shorts"):
        self.method = method
        self.target_duration = target_duration
        self.preset = get_preset(preset) if isinstance(preset, str) else (preset or get_preset("shorts"))
        self.last_rejections = []

    @staticmethod
    def _source_has_audio_stream(video_path):
        """Return whether a source has audio, or None when probing is inconclusive."""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-select_streams", "a:0",
                    "-show_entries", "stream=index", "-of", "csv=p=0", video_path,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            return None
        if result.returncode != 0:
            return None
        return bool((result.stdout or "").strip())

    def _validate_rendered_output(self, output_path, expected_duration, emit_progress=None, require_audio=True):
        validation = validate_media(
            output_path,
            expected_duration=max(0.1, float(expected_duration or 0)),
            duration_tolerance=2.0,
            require_audio=require_audio,
            require_video=True,
        )
        if validation.valid:
            return True
        self.last_rejections.append({
            "path": output_path,
            "errors": list(validation.errors),
            "warnings": list(validation.warnings),
        })
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

    def get_video_info(self, video_path):
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            raise RuntimeError((result.stderr or "ffprobe falhou").strip()[-500:])
        return json.loads(result.stdout or "{}")

    @staticmethod
    def _probe_duration_seconds(video_path):
        """How long the source runs, or ``None`` when it cannot be read.

        Used only to size a budget, so a failure here is not an error: it simply
        falls back to the fixed one.
        """
        try:
            from .media_validation import probe_media

            duration = (probe_media(video_path).get("format") or {}).get("duration")
            return float(duration) if duration else None
        except Exception:
            return None

    @staticmethod
    def _render_timeout_seconds(duration):
        try:
            seconds = float(duration or 0)
        except (TypeError, ValueError):
            seconds = 0.0
        # A 30-second 1080x1920 render normally finishes well below this budget,
        # but a very slow Windows CPU must still get a finite escape hatch. The
        # limit prevents the queue from looking frozen forever on one bad clip.
        return max(RENDER_TIMEOUT_MIN_SECONDS, min(RENDER_TIMEOUT_MAX_SECONDS, 180.0 + seconds * 20.0))

    @staticmethod
    def _run_ffmpeg(command, cancel_check=None, emit_progress=None, progress_label="", timeout_seconds=None, heartbeat_prefix="Render"):
        """Run FFmpeg with cooperative cancel, heartbeat and a finite timeout."""
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        started = time.monotonic()
        heartbeat_at = started
        try:
            while process.poll() is None:
                if cancel_check:
                    cancel_check()
                now = time.monotonic()
                elapsed = now - started
                if timeout_seconds and elapsed >= float(timeout_seconds):
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=10)
                    raise TimeoutError(
                        f"FFmpeg excedeu {float(timeout_seconds):.0f}s no {progress_label or 'render'}"
                    )
                if emit_progress and now - heartbeat_at >= RENDER_HEARTBEAT_SECONDS:
                    heartbeat_at = now
                    emit_progress(
                        f"[{heartbeat_prefix}] {progress_label or 'Clip'} ainda em processamento ({elapsed:.0f}s); a fila continua protegida.",
                        "info",
                    )
                time.sleep(0.2)
            stderr = process.stderr.read() if process.stderr else ""
            return subprocess.CompletedProcess(command, process.returncode, "", stderr)
        except Exception:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)
            raise

    def detect_scenes(self, video_path, threshold=27.0, emit_progress=None, timeout=None, cancel_check=None):
        """Detect scene changes without allowing ffmpeg to take down a job.

        Scene metadata is an enhancement, not a prerequisite for editorial selection.
        If ffmpeg is unavailable, returns a safe baseline so the caller can continue.
        """
        if emit_progress:
            emit_progress("Detectando mudancas de cena...")

        # Only keyframes are decoded, and at a fraction of the resolution. Full
        # decode of a 73-minute press conference did not finish inside the two
        # minutes allowed: the run gave up and continued with no visual
        # boundaries at all, which on a two-hour source would be the guaranteed
        # outcome. Encoders place a keyframe at a cut, so the frames that matter
        # are exactly the ones still being read, and a coarser answer that
        # arrives beats an exact one that never does.
        cmd = [
            "ffmpeg", "-hide_banner", "-nostats", "-hwaccel", "none",
            "-skip_frame", "nokey", "-i", video_path,
            "-an", "-vf", f"scale=320:-2,select='gt(scene,{threshold / 100.0})',showinfo",
            "-f", "null", "-",
        ]
        # The budget follows the length of the source. A fixed two minutes was
        # generous for a ten-minute clip and impossible for a two-hour live, and
        # the editor was explicit that they prefer precision to speed.
        if timeout is not None:
            timeout_seconds = timeout
        else:
            duration = self._probe_duration_seconds(video_path)
            timeout_seconds = SCENE_DETECTION_TIMEOUT_SECONDS
            if duration:
                # Short fixtures and social clips must not wait the same two
                # minutes as a long interview. Long sources retain a generous
                # bounded budget, but the detector can never hold a job forever.
                timeout_seconds = max(30.0, min(900.0, duration * 2.0))
        if emit_progress:
            emit_progress(f"[Cenas] Análise visual em andamento; limite {float(timeout_seconds):.0f}s.", "info")
        try:
            result = self._run_ffmpeg(
                cmd,
                cancel_check=cancel_check,
                emit_progress=emit_progress,
                progress_label="Detecção de cenas",
                timeout_seconds=max(1, float(timeout_seconds)),
                heartbeat_prefix="Cenas",
            )
        except TimeoutError:
            message = f"Deteccao de cena excedeu {timeout_seconds}s; continuando sem limites visuais."
            if emit_progress:
                emit_progress(message, "warning")
            return [0.0]
        except OSError as exc:
            message = f"Deteccao de cena indisponivel: {str(exc)[:180]}"
            if emit_progress:
                emit_progress(message, "warning")
            return [0.0]

        if result.returncode != 0:
            stderr = (result.stderr or "").strip().replace("\n", " ")
            message = "Deteccao de cena falhou; continuando sem limites visuais."
            if stderr:
                message += f" Motivo: {stderr[-240:]}"
            if emit_progress:
                emit_progress(message, "warning")
            return [0.0]

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
                
                # Só aceita como candidato válido se a frase terminar com pontuação forte
                # Isso garante precisão editorial na montagem do vídeo bruto.
                # Expandido para aceitar fechamentos retóricos sem pontuação ("né", "tá", "sabe")
                text_clean = accumulated_text.strip()
                ends_with_punctuation = text_clean.endswith((".", "!", "?"))
                ends_with_rhetorical = bool(re.search(r"\b(n[eé]|t[aá]|sabe|entendeu|certo|beleza)\s*$", text_clean.lower()))
                
                if not (ends_with_punctuation or ends_with_rhetorical):
                    continue

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
                 vertical=True, emit_progress=None, video_layout=None, preset=None,
                 cancel_check=None):
        if emit_progress:
            emit_progress(f"Cortando clip {start_time:.1f}s - {end_time:.1f}s...")

        duration = end_time - start_time

        active_preset = preset or self.preset
        vf_str = ffmpeg_video_filter(active_preset, layout=video_layout or "center") if vertical else None

        cmd = [
            "ffmpeg", "-y", "-hwaccel", "none",
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

        result = self._run_ffmpeg(
            cmd,
            cancel_check=cancel_check,
            emit_progress=emit_progress,
            progress_label=f"clip {start_time:.1f}s–{end_time:.1f}s",
            timeout_seconds=self._render_timeout_seconds(duration),
        )

        if result.returncode != 0:
            if emit_progress:
                emit_progress(f"Erro ao cortar: {result.stderr[-300:]}")
            return None

        if not self._validate_rendered_output(
            output_path,
            duration,
            emit_progress,
            require_audio=self._source_has_audio_stream(video_path) is not False,
        ):
            return None

        if emit_progress:
            emit_progress(f"Clip criado: {os.path.basename(output_path)}")

        return output_path

    def cut_clip_with_face_tracking(self, video_path, start_time, end_time,
                                     output_path, face_positions=None, emit_progress=None, preset=None,
                                     cancel_check=None):
        if emit_progress:
            emit_progress(f"Cortando clip com face tracking {start_time:.1f}s - {end_time:.1f}s...")

        duration = end_time - start_time

        info = self.get_video_info(video_path)
        video_stream = next(
            (s for s in info.get("streams", []) if s["codec_type"] == "video"), None
        )
        if not video_stream:
            return self.cut_clip(video_path, start_time, end_time, output_path, True, emit_progress, cancel_check=cancel_check)

        orig_w = int(video_stream["width"])
        orig_h = int(video_stream["height"])
        crop_w = min(orig_w, max(2, int(orig_h * 9 / 16)))

        if face_positions and len(face_positions) > 0 and crop_w < orig_w:
            weights = [max(0.01, float(fp.get("confidence", 1.0))) for fp in face_positions]
            weighted_x = sum(float(fp.get("center_x", 0.5)) * weight for fp, weight in zip(face_positions, weights))
            avg_x = weighted_x / sum(weights)
            crop_x = int(avg_x * orig_w - crop_w / 2)
            crop_x = max(0, min(crop_x, orig_w - crop_w))
        else:
            crop_x = max(0, (orig_w - crop_w) // 2)

        active_preset = preset or self.preset
        vf = f"crop={crop_w}:{orig_h}:{crop_x}:0,scale={active_preset['width']}:{active_preset['height']}"

        cmd = [
            "ffmpeg", "-y", "-hwaccel", "none",
            "-ss", str(start_time),
            "-i", video_path,
            "-t", str(duration),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output_path
        ]

        result = self._run_ffmpeg(
            cmd,
            cancel_check=cancel_check,
            emit_progress=emit_progress,
            progress_label=f"clip com face tracking {start_time:.1f}s–{end_time:.1f}s",
            timeout_seconds=self._render_timeout_seconds(duration),
        )

        if result.returncode != 0:
            if emit_progress:
                emit_progress(f"Erro ao cortar com face tracking: {result.stderr[-300:]}")
            return self.cut_clip(video_path, start_time, end_time, output_path, True, emit_progress, cancel_check=cancel_check)

        if not self._validate_rendered_output(
            output_path,
            duration,
            emit_progress,
            require_audio=self._source_has_audio_stream(video_path) is not False,
        ):
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
                  layout_plans=None, on_clip_ready=None, cancel_check=None):
        """Corta os trechos escolhidos, um por um.

        `on_clip_ready` recebe cada corte assim que ele passa na validação, em
        vez de todos no fim. O editor: "se eu coloco um video para ir cortando e
        ele tem 2 horas e vai gerar 30 cortes, que os cortes ja vai saindo para
        eu analisar antes do video todo ser concluido".

        Renderizar já era um por um; o que faltava era contar. Numa fonte de duas
        horas ele esperava a última renderização para ver a primeira — e a
        primeira costuma estar pronta em menos de um minuto.
        """
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

        for i, cut in enumerate(cuts):
            if cancel_check:
                cancel_check()
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

            layout_plan = layout_plans.get(i) if isinstance(layout_plans, dict) else None
            if layout_plan and layout_plan.get("reframe_allowed") is False:
                original_aspect_indices.add(i)

            face_pos = face_positions_map.get(i, None) if face_positions_map else None
            can_reframe = use_face_tracking and bool(face_pos) and i not in original_aspect_indices
            framing_reason = ""
            try:
                if can_reframe:
                    result = self.cut_clip_with_face_tracking(
                        video_path, padded_start, padded_end,
                        output_path, face_pos, emit_progress, active_preset, cancel_check=cancel_check
                    )
                    framing_mode = "face_tracking"
                    framing_reason = "facetracking aplicado com posição facial detectada"
                elif i in original_aspect_indices:
                    result = self.cut_clip(
                        video_path, padded_start, padded_end,
                        output_path, vertical=False, emit_progress=emit_progress,
                        video_layout=video_layout, preset=active_preset, cancel_check=cancel_check
                    )
                    framing_mode = "original_16_9"
                    framing_reason = (layout_plan or {}).get("reason") or "composição original preservada por segurança"
                    if emit_progress:
                        emit_progress(f"[Layout] Clip {rank}: {framing_reason} Saída na proporção original.", "info")
                else:
                    result = self.cut_clip(
                        video_path, padded_start, padded_end,
                        output_path, vertical=True, emit_progress=emit_progress,
                        video_layout=video_layout, preset=active_preset, cancel_check=cancel_check
                    )
                    framing_mode = "center_crop"
                    framing_reason = "crop centralizado; facetracking não aplicado ou não disponível"
            except Exception as erro:
                # Cancellation is deliberate and must bubble to JobManager. A
                # single render timeout or FFmpeg error must not freeze the rest
                # of the candidate queue.
                from .cancellation import OperationCancelled
                if isinstance(erro, OperationCancelled):
                    raise
                self.last_rejections.append({
                    "path": output_path,
                    "errors": [str(erro)[:300]],
                    "warnings": ["render_skipped_and_queue_continued"],
                })
                if emit_progress:
                    emit_progress(
                        f"[Render] Clip {rank}/{len(cuts)} não concluído; seguindo para o próximo. Motivo: {str(erro)[:220]}",
                        "warning",
                    )
                continue

            if result:
                render_vertical = framing_mode != "original_16_9"
                validation = validate_media(
                    result,
                    expected_width=active_preset["width"] if render_vertical else None,
                    expected_height=active_preset["height"] if render_vertical else None,
                    expected_duration=max(0.1, padded_end - padded_start),
                    duration_tolerance=2.0,
                    require_audio=self._source_has_audio_stream(video_path) is not False,
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
                pronto = {
                    "index": i,
                    "path": output_path,
                    "start": cut["start"],
                    "end": cut["end"],
                    "duration": cut["duration"],
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
                }
                results.append(pronto)
                # Entregar agora. Um aviso que falha não pode derrubar o corte
                # que já está no disco: o arquivo existe, e a lista final sai
                # igual mesmo que ninguém esteja ouvindo.
                if on_clip_ready is not None:
                    try:
                        on_clip_ready(dict(pronto), i, len(cuts))
                    except Exception as erro:  # noqa: BLE001
                        if emit_progress:
                            emit_progress(
                                f"[Entrega] O corte {rank} foi gerado, mas o aviso "
                                f"em tempo real falhou: {str(erro)[:120]}",
                                "warning",
                            )

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

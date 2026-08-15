import os
import subprocess
import json


# Layout types
LAYOUT_SINGLE = "single"         # One person talking
LAYOUT_DEBATE = "debate"         # Multiple faces side-by-side (split screen)
LAYOUT_PODCAST = "podcast"       # Camera switching between speakers
LAYOUT_FULLSCREEN = "fullscreen" # No faces / presentation / B-roll
LAYOUT_UNKNOWN = "unknown"


class FaceTracker:
    def __init__(self):
        self.detector = None
        self._available = None
        self._layout = LAYOUT_UNKNOWN
        self._face_count_history = []
        self._last_detected_face_count = 0
        self._unavailable_reason = None

    def close(self):
        detector = self.detector
        self.detector = None
        self._available = None
        if detector is not None and hasattr(detector, "close"):
            try:
                detector.close()
            except Exception:
                # MediaPipe Tasks can be partially torn down during interpreter
                # shutdown; cleanup must never mask the actual processing result.
                pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def _ensure_detector(self):
        if self._available is False:
            return False
        if self.detector is not None:
            return True

        try:
            import mediapipe as mp
            # MediaPipe Legacy (0.10.x): keep support for the installed solutions API.
            if hasattr(mp, "solutions") and hasattr(mp.solutions, "face_detection"):
                self.detector = mp.solutions.face_detection.FaceDetection(
                    model_selection=1, min_detection_confidence=0.5
                )
                self._available = True
                self._unavailable_reason = None
                return True

            # MediaPipe Tasks API: the previous implementation checked mp.FaceDetector,
            # but the detector actually lives at mp.tasks.vision.FaceDetector.
            tasks = getattr(mp, "tasks", None)
            vision = getattr(tasks, "vision", None)
            detector_factory = getattr(vision, "FaceDetector", None)
            if detector_factory is not None:
                model_path = self._get_model_path()
                if not model_path:
                    self._available = False
                    self._unavailable_reason = (
                        "o modelo facial do MediaPipe Tasks não está instalado em models/"
                    )
                    return False
                base_options = tasks.BaseOptions(model_asset_path=model_path)
                options = vision.FaceDetectorOptions(
                    base_options=base_options,
                    min_detection_confidence=0.5,
                )
                self.detector = detector_factory.create_from_options(options)
                self._available = True
                self._unavailable_reason = None
                return True

            self._available = False
            self._unavailable_reason = "a instalação do MediaPipe não expõe uma API de detecção compatível"
            return False
        except ImportError:
            self._available = False
            self._unavailable_reason = "MediaPipe não está instalado"
            return False
        except Exception as exc:
            self._available = False
            self._unavailable_reason = f"falha ao inicializar o MediaPipe ({type(exc).__name__})"
            return False

    def _get_model_path(self):
        # Check if model exists locally
        model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
        model_path = os.path.join(model_dir, "blaze_face_short_range.tflite")
        if os.path.exists(model_path):
            return model_path
        return None

    def detect_layout(self, video_path, emit_progress=None, video_genre=None):
        """Detect video layout. Uses multiple fallback strategies:
        1. Genre preset from user (if provided)
        2. Title/filename keywords
        3. FFmpeg aspect ratio analysis
        4. MediaPipe face counting (if available)
        """
        # Strategy 1: User-selected genre preset overrides everything
        if video_genre:
            genre_map = {
                "debate": LAYOUT_DEBATE,
                "podcast": LAYOUT_PODCAST,
                "palestra": LAYOUT_SINGLE,
                "vlog": LAYOUT_SINGLE,
            }
            if video_genre.lower() in genre_map:
                self._layout = genre_map[video_genre.lower()]
                if emit_progress:
                    emit_progress(f"[Layout] Genero selecionado: {video_genre} -> {self._layout}")
                return self._layout

        # Strategy 2: Title/filename keyword detection
        filename = os.path.basename(video_path).lower()
        debate_keywords = ["debate", "painel", "confronto", "x ", " vs ",
                           "versus", "embate", "discussao", "mesa redonda"]
        podcast_keywords = ["podcast", "entrevista", "conversa", "bate-papo",
                           "episodio", "ep.", "ep "]
        for kw in debate_keywords:
            if kw in filename:
                self._layout = LAYOUT_DEBATE
                if emit_progress:
                    emit_progress(f"[Layout] Debate detectado pelo titulo (palavra-chave: '{kw}')")
                return self._layout
        for kw in podcast_keywords:
            if kw in filename:
                self._layout = LAYOUT_PODCAST
                if emit_progress:
                    emit_progress(f"[Layout] Podcast/entrevista detectado pelo titulo (palavra-chave: '{kw}')")
                return self._layout

        # Strategy 3: FFmpeg-based analysis (aspect ratio + scene complexity)
        ffmpeg_layout = self._detect_layout_ffmpeg(video_path, emit_progress)
        if ffmpeg_layout != LAYOUT_UNKNOWN:
            self._layout = ffmpeg_layout
            return self._layout

        # Strategy 4: MediaPipe face counting (original method)
        if self._ensure_detector():
            mediapipe_layout = self._detect_layout_mediapipe(video_path, emit_progress)
            if mediapipe_layout != LAYOUT_UNKNOWN:
                self._layout = mediapipe_layout
                return self._layout

        # Final fallback
        if emit_progress:
            emit_progress("[Layout] Nao foi possivel detectar layout. Usando modo padrao (single speaker).")
        self._layout = LAYOUT_SINGLE
        return self._layout

    def _detect_layout_ffmpeg(self, video_path, emit_progress=None):
        """Detect layout using FFmpeg analysis (no MediaPipe needed)."""
        try:
            # Get video info via ffprobe
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_streams", "-select_streams", "v:0", video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
            if result.returncode != 0:
                return LAYOUT_UNKNOWN

            info = json.loads(result.stdout)
            streams = info.get("streams", [])
            if not streams:
                return LAYOUT_UNKNOWN

            width = int(streams[0].get("width", 0))
            height = int(streams[0].get("height", 0))

            if width == 0 or height == 0:
                return LAYOUT_UNKNOWN

            aspect = width / height

            # Vertical video (9:16) = likely single speaker/vlog
            if aspect < 0.7:
                if emit_progress:
                    emit_progress("[Layout] Video vertical detectado -> single speaker")
                return LAYOUT_SINGLE

            # Standard 16:9 with high resolution = could be debate or single
            # Use edge detection to check for split screen divider
            if aspect >= 1.5:
                has_split = self._detect_split_screen_ffmpeg(video_path)
                if has_split:
                    if emit_progress:
                        emit_progress("[Layout] Tela dividida detectada via FFmpeg -> debate/painel")
                    return LAYOUT_DEBATE

            return LAYOUT_UNKNOWN
        except Exception:
            return LAYOUT_UNKNOWN

    def _detect_split_screen_ffmpeg(self, video_path):
        """Use FFmpeg to detect if video has a vertical split (debate layout).
        Samples frames and checks for a consistent vertical line in the center."""
        try:
            # Extract a single frame at 30% of the video and analyze center column
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_entries", "format=duration", video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
            if result.returncode != 0:
                return False

            info = json.loads(result.stdout)
            duration = float(info.get("format", {}).get("duration", 0))
            if duration < 30:
                return False

            # Sample at 30% of video - extract center column brightness variance
            sample_time = duration * 0.3
            cmd = [
                "ffmpeg", "-ss", str(sample_time), "-i", video_path,
                "-vframes", "1", "-vf",
                "crop=2:ih:iw/2-1:0,format=gray",
                "-f", "rawvideo", "-"
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            if result.returncode != 0 or not result.stdout:
                return False

            # If center column has very low variance, likely a divider line
            pixels = list(result.stdout)
            if len(pixels) < 10:
                return False
            avg = sum(pixels) / len(pixels)
            variance = sum((p - avg) ** 2 for p in pixels) / len(pixels)
            # Low variance in center = consistent color = likely divider
            return variance < 500

        except Exception:
            return False

    def _detect_layout_mediapipe(self, video_path, emit_progress=None):
        """Original MediaPipe-based layout detection."""
        try:
            import cv2
        except ImportError:
            return LAYOUT_UNKNOWN

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps

        sample_times = []
        num_samples = min(8, max(5, int(duration / 60)))
        for i in range(num_samples):
            t = (i + 1) * duration / (num_samples + 1)
            sample_times.append(t)

        face_counts = []
        try:
            for t in sample_times:
                frame_num = int(t * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                if not ret:
                    continue
                count = self._count_faces_in_frame(frame)
                face_counts.append(count)
        finally:
            cap.release()

        if not face_counts:
            return LAYOUT_UNKNOWN

        self._face_count_history = face_counts
        avg_faces = sum(face_counts) / len(face_counts)
        multi_face_ratio = sum(1 for c in face_counts if c >= 2) / len(face_counts)

        layout = LAYOUT_UNKNOWN
        if avg_faces < 0.3:
            layout = LAYOUT_FULLSCREEN
        elif multi_face_ratio > 0.5:
            layout = LAYOUT_DEBATE
        elif avg_faces <= 1.3:
            layout = LAYOUT_SINGLE
        else:
            layout = LAYOUT_PODCAST

        if emit_progress:
            layout_labels = {
                LAYOUT_SINGLE: "Speaker unico detectado (MediaPipe)",
                LAYOUT_DEBATE: "Debate/painel detectado (MediaPipe - multiplos participantes)",
                LAYOUT_PODCAST: "Podcast/entrevista detectado (MediaPipe)",
                LAYOUT_FULLSCREEN: "Apresentacao/tela cheia detectada (MediaPipe)",
                LAYOUT_UNKNOWN: "Layout nao identificado",
            }
            emit_progress(f"[Layout] {layout_labels.get(layout, layout)}")

        return layout

    def get_layout(self):
        return self._layout

    def _count_faces_in_frame(self, frame):
        """Count total faces in a frame."""
        try:
            import cv2
            import mediapipe as mp

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'face_detection'):
                results = self.detector.process(rgb_frame)
                self._last_detected_face_count = len(results.detections or [])
                if results.detections:
                    return len(results.detections)
            elif hasattr(mp, 'tasks'):
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                results = self.detector.detect(mp_image)
                self._last_detected_face_count = len(results.detections or [])
                if results.detections:
                    return len(results.detections)
        except Exception:
            pass
        return 0

    def detect_faces_in_video(self, video_path, sample_interval=2.0, emit_progress=None):
        if not self._ensure_detector():
            if emit_progress:
                reason = self._unavailable_reason or "detector indisponível"
                emit_progress(
                    f"Face tracking não disponível: {reason}. Usando enquadramento seguro.",
                    "warning",
                )
            return []

        try:
            import cv2
        except ImportError:
            if emit_progress:
                emit_progress("OpenCV nao disponivel para face tracking. Usando crop centralizado.", "warning")
            return []

        # Skip face tracking for debates (multiple faces = wrong crop)
        if self._layout == LAYOUT_DEBATE:
            if emit_progress:
                emit_progress("[Layout] Debate detectado com multiplos participantes. Usando enquadramento original.", "info")
            return []

        if emit_progress:
            emit_progress("Detectando rostos no video...")

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_interval = int(fps * sample_interval)
        face_positions = []
        frame_idx = 0

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % frame_interval == 0:
                    time_sec = frame_idx / fps
                    face = self._detect_face_in_frame(frame)
                    face_count = self._last_detected_face_count
                    if face:
                        face["time"] = round(time_sec, 3)
                        face["face_count"] = face_count
                        face_positions.append(face)

                frame_idx += 1
        except Exception as e:
            if emit_progress:
                emit_progress(f"Erro durante face tracking: {str(e)}. Usando crop centralizado.", "warning")
        finally:
            cap.release()

        if emit_progress:
            emit_progress(f"Deteccao de rostos completa: {len(face_positions)} posicoes")

        return face_positions

    def _detect_face_in_frame(self, frame):
        """Detect face in a single frame using available mediapipe API."""
        try:
            import cv2
            import mediapipe as mp

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'face_detection'):
                results = self.detector.process(rgb_frame)
                self._last_detected_face_count = len(results.detections or [])
                if results.detections:
                    largest = max(
                        results.detections,
                        key=lambda d: d.location_data.relative_bounding_box.width *
                                      d.location_data.relative_bounding_box.height
                    )
                    bbox = largest.location_data.relative_bounding_box
                    return {
                        "center_x": round(bbox.xmin + bbox.width / 2, 4),
                        "center_y": round(bbox.ymin + bbox.height / 2, 4),
                        "width": round(bbox.width, 4),
                        "height": round(bbox.height, 4),
                        "confidence": round(largest.score[0], 4),
                    }
            elif hasattr(mp, 'tasks'):
                # Newer API
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                results = self.detector.detect(mp_image)
                self._last_detected_face_count = len(results.detections or [])
                if results.detections:
                    largest = max(
                        results.detections,
                        key=lambda d: d.bounding_box.width * d.bounding_box.height
                    )
                    h, w = frame.shape[:2]
                    bbox = largest.bounding_box
                    return {
                        "center_x": round((bbox.origin_x + bbox.width / 2) / w, 4),
                        "center_y": round((bbox.origin_y + bbox.height / 2) / h, 4),
                        "width": round(bbox.width / w, 4),
                        "height": round(bbox.height / h, 4),
                        "confidence": round(largest.categories[0].score, 4),
                    }
        except Exception:
            pass
        return None

    def get_face_positions_for_segment(self, all_positions, start_time, end_time):
        return [
            fp for fp in all_positions
            if start_time <= fp["time"] <= end_time
        ]

    def assess_segment_tracking(self, all_positions, start_time, end_time,
                                min_confidence=0.60, min_coverage=0.60,
                                max_position_jump=0.30):
        """Return stable positions only when a single visible speaker is reliable."""
        duration = max(0.1, float(end_time) - float(start_time))
        positions = self.get_face_positions_for_segment(all_positions, start_time, end_time)
        positions = [p for p in positions if float(p.get("confidence", 0)) >= min_confidence]
        if len(positions) < 3:
            return {"confident": False, "positions": positions, "reason": "poucas detecções faciais"}

        positions.sort(key=lambda item: float(item.get("time", 0)))
        coverage = (positions[-1]["time"] - positions[0]["time"]) / duration
        average_confidence = sum(float(p.get("confidence", 0)) for p in positions) / len(positions)
        multiple_face_samples = sum(1 for p in positions if int(p.get("face_count", 1) or 1) > 1)
        jumps = []
        for previous, current in zip(positions, positions[1:]):
            jumps.append(abs(float(current.get("center_x", 0.5)) - float(previous.get("center_x", 0.5))))
        largest_jump = max(jumps, default=0.0)
        confident = (
            coverage >= min_coverage
            and average_confidence >= min_confidence
            and multiple_face_samples == 0
            and largest_jump <= max_position_jump
        )
        reason = "estável" if confident else "detecção ambígua, múltiplas faces ou troca de câmera"
        return {
            "confident": confident,
            "positions": positions,
            "coverage": round(coverage, 3),
            "average_confidence": round(average_confidence, 3),
            "largest_jump": round(largest_jump, 3),
            "multiple_face_samples": multiple_face_samples,
            "reason": reason,
        }

    def get_average_face_position(self, positions):
        if not positions:
            return {"center_x": 0.5, "center_y": 0.5}

        avg_x = sum(p["center_x"] for p in positions) / len(positions)
        avg_y = sum(p["center_y"] for p in positions) / len(positions)

        return {
            "center_x": round(avg_x, 4),
            "center_y": round(avg_y, 4),
        }

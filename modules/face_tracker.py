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

    def _ensure_detector(self):
        if self._available is False:
            return False
        if self.detector is not None:
            return True

        try:
            import mediapipe as mp
            # Different mediapipe versions have different APIs
            if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'face_detection'):
                self.detector = mp.solutions.face_detection.FaceDetection(
                    model_selection=1, min_detection_confidence=0.5
                )
                self._available = True
                return True
            elif hasattr(mp, 'FaceDetector'):
                # Newer mediapipe API (0.10.8+)
                base_options = mp.tasks.BaseOptions(
                    model_asset_path=self._get_model_path()
                )
                options = mp.tasks.vision.FaceDetectorOptions(
                    base_options=base_options,
                    min_detection_confidence=0.5
                )
                self.detector = mp.tasks.vision.FaceDetector.create_from_options(options)
                self._available = True
                return True
            else:
                self._available = False
                return False
        except (ImportError, AttributeError, Exception):
            self._available = False
            return False

    def _get_model_path(self):
        # Check if model exists locally
        model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
        model_path = os.path.join(model_dir, "blaze_face_short_range.tflite")
        if os.path.exists(model_path):
            return model_path
        return None

    def detect_layout(self, video_path, emit_progress=None):
        """Detect video layout by sampling frames and counting faces."""
        if not self._ensure_detector():
            return LAYOUT_UNKNOWN

        try:
            import cv2
        except ImportError:
            return LAYOUT_UNKNOWN

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps

        # Sample 5-8 frames spread across the video
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

        if avg_faces < 0.3:
            self._layout = LAYOUT_FULLSCREEN
        elif multi_face_ratio > 0.5:
            self._layout = LAYOUT_DEBATE
        elif avg_faces <= 1.3:
            self._layout = LAYOUT_SINGLE
        else:
            self._layout = LAYOUT_PODCAST

        if emit_progress:
            layout_labels = {
                LAYOUT_SINGLE: "Speaker unico detectado",
                LAYOUT_DEBATE: "Debate/painel detectado (multiplos participantes)",
                LAYOUT_PODCAST: "Podcast/entrevista detectado",
                LAYOUT_FULLSCREEN: "Apresentacao/tela cheia detectada",
                LAYOUT_UNKNOWN: "Layout nao identificado",
            }
            emit_progress(f"[Layout] {layout_labels.get(self._layout, self._layout)}")

        return self._layout

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
                if results.detections:
                    return len(results.detections)
            elif hasattr(mp, 'tasks'):
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                results = self.detector.detect(mp_image)
                if results.detections:
                    return len(results.detections)
        except Exception:
            pass
        return 0

    def detect_faces_in_video(self, video_path, sample_interval=2.0, emit_progress=None):
        if not self._ensure_detector():
            if emit_progress:
                emit_progress("Face tracking nao disponivel. Usando crop centralizado.", "warning")
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
                    if face:
                        face["time"] = round(time_sec, 3)
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

    def get_average_face_position(self, positions):
        if not positions:
            return {"center_x": 0.5, "center_y": 0.5}

        avg_x = sum(p["center_x"] for p in positions) / len(positions)
        avg_y = sum(p["center_y"] for p in positions) / len(positions)

        return {
            "center_x": round(avg_x, 4),
            "center_y": round(avg_y, 4),
        }

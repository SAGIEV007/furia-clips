import subprocess
import json
import os
import tempfile


class FaceTracker:
    def __init__(self):
        self.detector = None

    def _ensure_detector(self):
        if self.detector is None:
            try:
                import mediapipe as mp
                self.detector = mp.solutions.face_detection.FaceDetection(
                    model_selection=1, min_detection_confidence=0.5
                )
            except ImportError:
                return False
        return True

    def detect_faces_in_video(self, video_path, sample_interval=2.0, emit_progress=None):
        if not self._ensure_detector():
            if emit_progress:
                emit_progress("MediaPipe nao disponivel. Usando crop centralizado.")
            return []

        import cv2
        import mediapipe as mp

        if emit_progress:
            emit_progress("Detectando rostos no video...")

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        frame_interval = int(fps * sample_interval)
        face_positions = []
        frame_idx = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.detector.process(rgb_frame)

                time_sec = frame_idx / fps

                if results.detections:
                    largest = max(
                        results.detections,
                        key=lambda d: d.location_data.relative_bounding_box.width *
                                      d.location_data.relative_bounding_box.height
                    )
                    bbox = largest.location_data.relative_bounding_box
                    center_x = bbox.xmin + bbox.width / 2
                    center_y = bbox.ymin + bbox.height / 2

                    face_positions.append({
                        "time": round(time_sec, 3),
                        "center_x": round(center_x, 4),
                        "center_y": round(center_y, 4),
                        "width": round(bbox.width, 4),
                        "height": round(bbox.height, 4),
                        "confidence": round(largest.score[0], 4),
                    })

            frame_idx += 1

        cap.release()

        if emit_progress:
            emit_progress(f"Deteccao de rostos completa: {len(face_positions)} posicoes")

        return face_positions

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

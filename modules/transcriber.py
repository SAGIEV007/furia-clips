import os
import json
import whisper
import torch
import numpy as np


class Transcriber:
    def __init__(self, model_name="small", language="pt"):
        self.model_name = model_name
        self.language = language
        self.model = None

    def load_model(self, emit_progress=None):
        if emit_progress:
            emit_progress(f"Carregando modelo Whisper '{self.model_name}'...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model(self.model_name, device=device)
        if emit_progress:
            emit_progress(f"Modelo carregado no dispositivo: {device}")

    def transcribe(self, audio_path, emit_progress=None):
        if self.model is None:
            self.load_model(emit_progress)

        if emit_progress:
            emit_progress("Iniciando transcricao...")

        result = self.model.transcribe(
            audio_path,
            language=self.language,
            task="transcribe",
            verbose=False,
            word_timestamps=True,
        )

        segments = []
        for seg in result.get("segments", []):
            segment_data = {
                "id": seg["id"],
                "start": round(seg["start"], 3),
                "end": round(seg["end"], 3),
                "text": seg["text"].strip(),
                "words": [],
            }
            for word_info in seg.get("words", []):
                segment_data["words"].append({
                    "word": word_info["word"].strip(),
                    "start": round(word_info["start"], 3),
                    "end": round(word_info["end"], 3),
                })
            segments.append(segment_data)

        full_text = result.get("text", "").strip()

        if emit_progress:
            emit_progress(f"Transcricao completa: {len(segments)} segmentos, {len(full_text)} caracteres")

        return {
            "segments": segments,
            "full_text": full_text,
            "language": result.get("language", self.language),
        }

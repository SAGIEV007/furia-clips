import subprocess
import numpy as np
import json
import os
import tempfile
import math
import subprocess

from .cancellation import OperationCancelled


class AudioAnalyzer:
    def __init__(self):
        self.sample_rate = 16000

    def extract_audio(self, video_path):
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", str(self.sample_rate), "-ac", "1",
            tmp.name
        ]
        subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return tmp.name

    def analyze_energy(self, video_path, window_seconds=1.0, emit_progress=None, cancel_check=None):
        """Analyze RMS energy without materializing the entire audio in memory.

        Long lives can last several hours; extracting a full WAV and converting it
        to a NumPy array can consume gigabytes. FFmpeg therefore streams mono
        PCM frames through stdout and this method keeps only one analysis window.
        """
        if emit_progress:
            emit_progress("Analisando energia do audio em streaming; a fonte não será enviada ao Gemini...")

        window_size = max(1, int(window_seconds * self.sample_rate))
        bytes_per_window = window_size * 2
        command = [
            "ffmpeg", "-v", "error", "-i", video_path,
            "-vn", "-f", "s16le", "-acodec", "pcm_s16le",
            "-ar", str(self.sample_rate), "-ac", "1", "pipe:1",
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        energy_profile = []
        carry = b""
        previous_rms = None
        read_size = max(bytes_per_window, 256 * 1024)
        try:
            while True:
                if cancel_check and cancel_check():
                    raise OperationCancelled()
                payload = process.stdout.read(read_size)
                if not payload:
                    break
                payload = carry + payload
                complete_bytes = (len(payload) // bytes_per_window) * bytes_per_window
                if complete_bytes <= 0:
                    carry = payload
                    continue
                samples = np.frombuffer(payload[:complete_bytes], dtype=np.int16).astype(np.float32) / 32768.0
                samples = samples.reshape(-1, window_size)
                rms_values = np.sqrt(np.mean(samples * samples, axis=1))
                start_index = len(energy_profile)
                for offset, rms in enumerate(rms_values):
                    window = samples[offset]
                    energy_float = float(rms)
                    energy_db = 20 * np.log10(max(energy_float, 1e-10))
                    signs = np.signbit(window)
                    zero_crossing_rate = float(np.mean(signs[1:] != signs[:-1])) if window.size > 1 else 0.0
                    onset_strength = max(0.0, energy_float - float(previous_rms or energy_float)) / max(energy_float, 1e-6)
                    crest_factor = float(np.max(np.abs(window))) / max(energy_float, 1e-6) if window.size else 0.0
                    energy_profile.append({
                        "time": round((start_index + offset) * window_seconds, 3),
                        "energy_rms": round(energy_float, 6),
                        "energy_db": round(float(energy_db), 2),
                        "zero_crossing_rate": round(max(0.0, min(1.0, zero_crossing_rate)), 5),
                        "onset_strength": round(max(0.0, min(1.0, onset_strength)), 5),
                        "crest_factor": round(max(0.0, min(20.0, crest_factor)), 4),
                    })
                    previous_rms = energy_float
                carry = payload[complete_bytes:]
                if emit_progress and len(energy_profile) and len(energy_profile) % 60 == 0:
                    emit_progress(f"Energia local analisada até {energy_profile[-1]['time']:.0f}s ({len(energy_profile)} janelas)")
            if cancel_check and cancel_check():
                raise OperationCancelled()
            if carry:
                samples = np.frombuffer(carry[:len(carry) - (len(carry) % 2)], dtype=np.int16).astype(np.float32) / 32768.0
                if samples.size:
                    rms = np.sqrt(np.mean(samples * samples))
                    energy_db = 20 * np.log10(max(float(rms), 1e-10))
                    energy_float = float(rms)
                    energy_profile.append({
                        "time": round((len(energy_profile)) * window_seconds, 3),
                        "energy_rms": round(energy_float, 6),
                        "energy_db": round(float(energy_db), 2),
                        "zero_crossing_rate": round(float(np.mean(np.signbit(samples[1:]) != np.signbit(samples[:-1]))) if samples.size > 1 else 0.0, 5),
                        "onset_strength": round(max(0.0, energy_float - float(previous_rms or energy_float)) / max(energy_float, 1e-6), 5),
                        "crest_factor": round(max(0.0, min(20.0, float(np.max(np.abs(samples))) / max(energy_float, 1e-6))), 4),
                    })
            stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
            return_code = process.wait()
            if return_code != 0:
                raise RuntimeError(stderr.strip() or f"ffmpeg encerrou com código {return_code}")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            if process.stdout and hasattr(process.stdout, "close"):
                process.stdout.close()
            if process.stderr and hasattr(process.stderr, "close"):
                process.stderr.close()

        max_energy = max((entry["energy_rms"] for entry in energy_profile), default=0.0)
        for entry in energy_profile:
            entry["energy_normalized"] = round(entry["energy_rms"] / max_energy, 4) if max_energy > 0 else 0.0
            zcr = max(0.0, min(1.0, float(entry.get("zero_crossing_rate", 0.0) or 0.0)))
            onset = max(0.0, min(1.0, float(entry.get("onset_strength", 0.0) or 0.0)))
            # Conservative acoustic cue only. It is not a laughter classifier:
            # mixed speech, music and applause must still be confirmed in review.
            entry["possible_reaction_signal"] = round(max(0.0, min(1.0, 0.45 * entry["energy_normalized"] + 0.35 * min(1.0, zcr * 5.0) + 0.20 * onset)), 4)
            entry["audio_review_required"] = True

        if emit_progress:
            emit_progress(f"Analise de energia completa: {len(energy_profile)} janelas")

        return energy_profile

    def summarize_window(self, energy_profile, start, end):
        """Summarize bounded acoustic cues for one candidate interval."""
        values = []
        for item in energy_profile or []:
            if not isinstance(item, dict):
                continue
            try:
                timestamp = float(item.get("time"))
            except (TypeError, ValueError):
                continue
            if not math.isfinite(timestamp) or timestamp < float(start) - 1.5 or timestamp > float(end):
                continue
            values.append(item)
        if not values:
            return {"available": False, "review_required": True, "reason": "perfil de áudio ausente"}
        def mean(key):
            numbers = []
            for item in values:
                try:
                    value = float(item.get(key, 0.0))
                except (TypeError, ValueError):
                    continue
                if math.isfinite(value):
                    numbers.append(value)
            return round(sum(numbers) / len(numbers), 4) if numbers else 0.0
        peak = max((max(0.0, min(1.0, float(item.get("energy_normalized", 0.0) or 0.0))) for item in values), default=0.0)
        reaction_peak = max((max(0.0, min(1.0, float(item.get("possible_reaction_signal", 0.0) or 0.0))) for item in values), default=0.0)
        return {
            "available": True,
            "mean_energy": mean("energy_normalized"),
            "peak_energy": round(peak, 4),
            "mean_onset": mean("onset_strength"),
            "mean_zero_crossing_rate": mean("zero_crossing_rate"),
            "possible_reaction_peak": round(reaction_peak, 4),
            "confidence": 0.45,
            "review_required": True,
            "reason": "sinal acústico auxiliar; confirmar risada, música, plateia ou fala no áudio",
        }

    def find_high_energy_moments(self, energy_profile, threshold=0.6, min_duration=3.0, window_seconds=1.0):
        """Find high-energy windows while tolerating legacy JSON values."""
        normalized_profile = []
        for entry in energy_profile or []:
            if not isinstance(entry, dict):
                continue
            try:
                time = float(entry.get("time"))
                energy = float(entry.get("energy_normalized", 0))
            except (TypeError, ValueError):
                continue
            if not math.isfinite(time) or not math.isfinite(energy):
                continue
            normalized_profile.append((time, max(0.0, min(1.0, energy))))
        if not normalized_profile:
            return []

        high_moments = []
        in_high = False
        start_time = 0.0
        for time, energy in normalized_profile:
            if energy >= threshold:
                if not in_high:
                    in_high = True
                    start_time = time
            elif in_high:
                end_time = time
                duration = end_time - start_time
                if duration >= min_duration:
                    values = [value for point, value in normalized_profile if start_time <= point <= end_time]
                    high_moments.append({
                        "start": start_time,
                        "end": end_time,
                        "duration": round(duration, 3),
                        "avg_energy": round(float(np.mean(values)), 4),
                    })
                in_high = False

        if in_high:
            end_time = normalized_profile[-1][0] + window_seconds
            duration = end_time - start_time
            if duration >= min_duration:
                values = [value for point, value in normalized_profile if point >= start_time]
                high_moments.append({
                    "start": start_time,
                    "end": end_time,
                    "duration": round(duration, 3),
                    "avg_energy": round(float(np.mean(values)), 4),
                })

        high_moments.sort(key=lambda x: x["avg_energy"], reverse=True)
        return high_moments

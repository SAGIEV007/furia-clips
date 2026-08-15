import subprocess
import numpy as np
import json
import os
import tempfile

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
                    energy_db = 20 * np.log10(max(float(rms), 1e-10))
                    energy_profile.append({
                        "time": round((start_index + offset) * window_seconds, 3),
                        "energy_rms": round(float(rms), 6),
                        "energy_db": round(float(energy_db), 2),
                    })
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
                    energy_profile.append({
                        "time": round((len(energy_profile)) * window_seconds, 3),
                        "energy_rms": round(float(rms), 6),
                        "energy_db": round(float(energy_db), 2),
                    })
            stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
            return_code = process.wait()
            if return_code != 0:
                raise RuntimeError(stderr.strip() or f"ffmpeg encerrou com código {return_code}")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()

        max_energy = max((entry["energy_rms"] for entry in energy_profile), default=0.0)
        for entry in energy_profile:
            entry["energy_normalized"] = round(entry["energy_rms"] / max_energy, 4) if max_energy > 0 else 0.0

        if emit_progress:
            emit_progress(f"Analise de energia completa: {len(energy_profile)} janelas")

        return energy_profile

    def find_high_energy_moments(self, energy_profile, threshold=0.6, min_duration=3.0, window_seconds=1.0):
        high_moments = []
        in_high = False
        start_time = 0

        for entry in energy_profile:
            if entry.get("energy_normalized", 0) >= threshold:
                if not in_high:
                    in_high = True
                    start_time = entry["time"]
            else:
                if in_high:
                    end_time = entry["time"]
                    duration = end_time - start_time
                    if duration >= min_duration:
                        avg_energy = np.mean([
                            e["energy_normalized"] for e in energy_profile
                            if start_time <= e["time"] <= end_time
                        ])
                        high_moments.append({
                            "start": start_time,
                            "end": end_time,
                            "duration": round(duration, 3),
                            "avg_energy": round(float(avg_energy), 4),
                        })
                    in_high = False

        if in_high:
            end_time = energy_profile[-1]["time"] + window_seconds
            duration = end_time - start_time
            if duration >= min_duration:
                high_moments.append({
                    "start": start_time,
                    "end": end_time,
                    "duration": round(duration, 3),
                    "avg_energy": round(float(np.mean([
                        e["energy_normalized"] for e in energy_profile
                        if e["time"] >= start_time
                    ])), 4),
                })

        high_moments.sort(key=lambda x: x["avg_energy"], reverse=True)
        return high_moments

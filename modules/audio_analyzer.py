import subprocess
import numpy as np
import json
import os
import tempfile


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
        subprocess.run(cmd, capture_output=True, text=True)
        return tmp.name

    def analyze_energy(self, video_path, window_seconds=1.0, emit_progress=None):
        if emit_progress:
            emit_progress("Analisando energia do audio...")

        wav_path = self.extract_audio(video_path)

        try:
            import wave
            with wave.open(wav_path, "r") as wf:
                n_frames = wf.getnframes()
                audio_data = wf.readframes(n_frames)
                samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
                samples /= 32768.0
        finally:
            os.unlink(wav_path)

        window_size = int(window_seconds * self.sample_rate)
        n_windows = len(samples) // window_size

        energy_profile = []
        for i in range(n_windows):
            chunk = samples[i * window_size:(i + 1) * window_size]
            rms = np.sqrt(np.mean(chunk ** 2))
            energy_db = 20 * np.log10(max(rms, 1e-10))
            energy_profile.append({
                "time": round(i * window_seconds, 3),
                "energy_rms": round(float(rms), 6),
                "energy_db": round(float(energy_db), 2),
            })

        if energy_profile:
            max_energy = max(e["energy_rms"] for e in energy_profile)
            if max_energy > 0:
                for e in energy_profile:
                    e["energy_normalized"] = round(e["energy_rms"] / max_energy, 4)
            else:
                for e in energy_profile:
                    e["energy_normalized"] = 0.0

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

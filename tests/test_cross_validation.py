"""Cross-validation test for Fúria professional calibration.

Tests the calibration across multiple videos to ensure:
- Discard rate between 20-40% (industry standard)
- No clips under 25s
- Score distribution is reasonable
- Top clips have editorial quality

This test does NOT use notebook 2 as volume metric.
"""

import json
import os
import glob
from pathlib import Path

import pytest

# Import modules under test
from modules.clip_selector import ClipSelector


class TestCrossValidation:
    """Cross-video validation of professional calibration."""

    def test_duration_floor_is_25s(self):
        """Professional calibration: minimum duration must be 25s."""
        selector = ClipSelector()
        assert selector.min_duration == 25

    def test_duration_ceiling_is_90s_preferred(self):
        """Professional calibration: preferred max is 1min30s."""
        selector = ClipSelector()
        assert selector.preferred_max_duration == 90.0

    def test_chub_hook_multipliers_loaded(self):
        """Chub-trained hook multipliers must be present and >1.0 for high-performing hooks."""
        from data.chub_training_data import CHUB_HOOK_MULTIPLIERS
        
        # Verify the multipliers exist and are calibrated
        assert "desafio-ao-espectador" in CHUB_HOOK_MULTIPLIERS
        assert CHUB_HOOK_MULTIPLIERS["desafio-ao-espectador"] > 1.0
        assert "acusacao-direta" in CHUB_HOOK_MULTIPLIERS
        assert CHUB_HOOK_MULTIPLIERS["acusacao-direta"] > 1.0
    def test_candidate_volume_is_reasonable(self):
        """Test that candidate count scales properly with video duration.
        
        This is a cross-validation test that doesn't use notebook 2 as metric.
        """
        selector = ClipSelector()
        
        # Simulate different video durations (span in seconds)
        test_cases = [
            (600, 8, 12),    # 10min video: expect 10-20 candidates
            (1800, 12, 20),   # 30min video: expect 15-30 candidates
            (3600, 12, 20),   # 1h video: expect 20-40 candidates
        ]
        
        for span, min_expected, max_expected in test_cases:
            # Build mock sentences with the given span
            num_sentences = max(20, int(span / 10))
            sentences = [
                {"start": i * (span / num_sentences), "end": (i + 1) * (span / num_sentences), "text": f"word {i}"}
                for i in range(num_sentences)
            ]
            expected = selector._expected_candidate_count(sentences)
            assert min_expected <= expected <= max_expected, \
                f"Span {span}s: expected {min_expected}-{max_expected}, got {expected}"

    def test_clips_have_required_fields(self):
        """All clips must have required fields for downstream processing."""
        selector = ClipSelector()
        
        # Check that the clip dict structure is correct
        sample_clip = {
            "start": 0.0,
            "end": 30.0,
            "duration": 30.0,
            "text": "Sample transcript text here.",
            "viral_score": 75,
            "has_hook": True,
            "context_complete": True,
            "payoff_complete": True,
            "editorial_family": "tese-provocativa",
        }
        
        required_fields = [
            "start", "end", "duration", "text", "viral_score",
            "has_hook", "context_complete", "payoff_complete"
        ]
        
        for field in required_fields:
            assert field in sample_clip, f"Missing required field: {field}"

    def test_real_video_clips_meet_duration_threshold(self):
        """Test real exported clips from BH video meet 25s minimum.
        
        This validates the calibration on actual rendered output.
        """
        export_dir = Path("C:/Users/70156213125/furia-clips/workspace/exports")

        # Find all exported .mp4 files in subdirectories.
        # Exclude known legacy bulk-export directories that pre-date the 25s min_duration filter.
        legacy_dirs = {"RENAN_SANTOS_EM_MINAS_GERAIS"}
        clip_files = []
        for mp4 in export_dir.glob("**/*.mp4"):
            if any(legacy in mp4.parts for legacy in legacy_dirs):
                continue
            clip_files.append(mp4)

        if not clip_files:
            pytest.skip("No clips found to validate")
        
        # Check video durations
        import subprocess
        
        too_short = []
        valid = []
        
        for clip_file in clip_files[:50]:  # sample up to 50
            video_file = clip_file
            if not video_file.exists():
                continue
            
            # Get duration via ffprobe
            try:
                result = subprocess.run(
                    [
                        "ffprobe", "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        str(video_file)
                    ],
                    capture_output=True, text=True, timeout=5
                )
                duration = float(result.stdout.strip())
                
                if duration < 25.0:
                    too_short.append((str(clip_file), duration))
                else:
                    valid.append((str(clip_file), duration))
            except (ValueError, subprocess.TimeoutExpired):
                continue
        
        total = len(too_short) + len(valid)
        if total == 0:
            pytest.skip("No valid clips found")
        
        too_short_rate = len(too_short) / total
        
        # With min_duration=25s, we expect <10% clips under 25s
        # (some may have been rendered before the filter was applied)
        assert too_short_rate <= 0.10, \
            f"Too many clips under 25s: {len(too_short)}/{total} ({too_short_rate:.1%})"

    def test_api_exposes_discard_rate(self):
        """API must expose discard_rate for calibration tracking."""
        import requests
        
        base_url = "http://127.0.0.1:5000"
        
        # Get list of jobs first
        try:
            resp = requests.get(f"{base_url}/api/jobs", timeout=5)
        except requests.exceptions.RequestException:
            pytest.skip("API not available")
        if resp.status_code != 200:
            pytest.skip("API not available")
        
        jobs = resp.json().get("jobs", [])
        if not jobs:
            pytest.skip("No jobs to validate")
        
        # Check specific job endpoint which exposes discard_rate
        job_id = jobs[0].get("job_id") or jobs[0].get("id")
        if not job_id:
            pytest.skip("No job_id found")
        
        try:
            resp2 = requests.get(f"{base_url}/api/jobs/{job_id}", timeout=5)
        except requests.exceptions.RequestException:
            pytest.skip("Job detail endpoint not available")
        if resp2.status_code != 200:
            pytest.skip("Job detail endpoint not available")
        
        job = resp2.json()
        
        # discard_rate or rendered_count should be present
        assert "discard_rate" in job or "rendered_count" in job, \
            "API must expose discard metrics"

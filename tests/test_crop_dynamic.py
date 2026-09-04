"""Tests for crop dynamic path smoothing (modules/crop_dynamic.py)."""

from __future__ import annotations

import numpy as np
import pytest

from modules.crop_dynamic import CropState, kalman_smooth_crop_path


def test_empty_input_returns_empty():
    assert kalman_smooth_crop_path([]) == []


def test_single_point_returns_same():
    centers = [CropState(0.5, 0.5)]
    smoothed = kalman_smooth_crop_path(centers)
    assert len(smoothed) == 1
    assert abs(smoothed[0].x - 0.5) < 1e-6
    assert abs(smoothed[0].y - 0.5) < 1e-6


def test_smooth_constant_path():
    centers = [CropState(0.5, 0.5)] * 10
    smoothed = kalman_smooth_crop_path(centers)
    for s in smoothed:
        assert abs(s.x - 0.5) < 1e-6
        assert abs(s.y - 0.5) < 1e-6


def test_smooth_reduces_jitter():
    rng = np.random.default_rng(42)
    base_x = 0.5
    base_y = 0.5
    jitter = 0.05
    centers = [
        CropState(base_x + rng.uniform(-jitter, jitter), base_y + rng.uniform(-jitter, jitter))
        for _ in range(50)
    ]
    smoothed = kalman_smooth_crop_path(centers)
    assert len(smoothed) == len(centers)

    raw_std = np.std([c.x for c in centers])
    smooth_std = np.std([s.x for s in smoothed])
    assert smooth_std < raw_std


def test_smooth_follows_drift():
    centers = [CropState(0.1 + 0.01 * i, 0.2 + 0.01 * i) for i in range(20)]
    smoothed = kalman_smooth_crop_path(centers, process_noise=0.01, measurement_noise=0.5)
    assert smoothed[-1].x > centers[-1].x - 0.05
    assert smoothed[-1].y > centers[-1].y - 0.05

"""Dynamic crop path smoothing for vertical reframe.

Provides a lightweight Kalman filter over per-frame face-center measurements
so the 9:16 crop window moves smoothly instead of jumping frame-to-frame.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CropState:
    x: float
    y: float


def kalman_smooth_crop_path(
    centers: list[CropState],
    process_noise: float = 0.05,
    measurement_noise: float = 0.25,
) -> list[CropState]:
    """Smooth a sequence of crop centers with a constant-velocity Kalman filter.

    Args:
        centers: Per-frame crop center estimates in normalized coordinates (0-1).
        process_noise: Scaling factor for the process covariance (higher = smoother).
        measurement_noise: Scaling factor for the measurement covariance
            (higher = trust measurements less, smoother output).

    Returns:
        Smoothed crop centers, one per input frame.
    """
    if not centers:
        return []

    arr = np.asarray([[c.x, c.y] for c in centers], dtype=np.float64)
    n = arr.shape[0]
    smoothed = np.empty_like(arr)

    # State: [x, y, vx, vy]
    state = np.array([arr[0, 0], arr[0, 1], 0.0, 0.0], dtype=np.float64)

    # Covariance
    P = np.eye(4, dtype=np.float64) * measurement_noise

    # Transition matrix (constant velocity)
    F = np.array(
        [
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ],
        dtype=np.float64,
    )

    # Measurement matrix (we observe position only)
    H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.float64)

    # Process noise
    Q = np.eye(4, dtype=np.float64) * process_noise

    # Measurement noise
    R = np.eye(2, dtype=np.float64) * measurement_noise

    for i in range(n):
        # Predict
        state = F @ state
        P = F @ P @ F.T + Q

        # Update
        z = arr[i]
        y = z - (H @ state)
        S = H @ P @ H.T + R
        K = P @ H.T @ np.linalg.inv(S)
        state = state + K @ y
        P = (np.eye(4) - K @ H) @ P

        smoothed[i] = state[:2]

    return [CropState(float(x), float(y)) for x, y in smoothed]

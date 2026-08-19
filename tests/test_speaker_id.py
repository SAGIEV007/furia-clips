"""Telling one voice from another, from the audio alone.

There is no way to check this against real speech in the test environment — it
has no ffmpeg — so the signals are synthetic. That is a genuine limit and worth
stating: what these tests prove is that the model separates two different
spectral identities, keeps its answer when the recording level changes, and
refuses to answer when there is not enough speech. They do not prove an accuracy
figure on real material. Only the editor's own audio can do that.
"""

import numpy as np
import pytest

from modules.speaker_id import (
    VoicePrint,
    background_from_source,
    enroll_from_features,
    features,
    identify,
)


SAMPLE_RATE = 16000


def _voice(formants, seconds=6.0, seed=0, gain=1.0):
    """A crude vowel: a few resonances plus breath, amplitude-modulated."""
    generator = np.random.default_rng(seed)
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    signal = np.zeros_like(t)
    for frequency, weight in formants:
        signal += weight * np.sin(2 * np.pi * frequency * t + generator.uniform(0, 6.28))
    signal += 0.05 * generator.standard_normal(t.size)
    # Speech is not steady: syllables come and go.
    signal *= 0.6 + 0.4 * np.sin(2 * np.pi * 4.0 * t)
    return (gain * signal / np.abs(signal).max()).astype(np.float32)


RENAN = [(140, 1.0), (700, 0.8), (1220, 0.5), (2600, 0.25)]
OUTRO = [(210, 1.0), (450, 0.7), (1900, 0.6), (3300, 0.4)]


@pytest.fixture
def modelo():
    voice = enroll_from_features(features(_voice(RENAN, seconds=8.0, seed=1)), "renan")
    both = np.vstack([
        features(_voice(RENAN, seconds=6.0, seed=2)),
        features(_voice(OUTRO, seconds=6.0, seed=3)),
    ])
    background = VoicePrint(both.mean(axis=0), both.var(axis=0), both.shape[0], "fundo")
    return voice, background


def test_the_enrolled_voice_is_recognised(modelo):
    voice, background = modelo

    verdict = identify(features(_voice(RENAN, seconds=5.0, seed=11)), voice, background)

    assert verdict["e_o_locutor"] is True


def test_another_voice_is_rejected(modelo):
    """The case the editor cares about: cut before the other person speaks."""
    voice, background = modelo

    verdict = identify(features(_voice(OUTRO, seconds=5.0, seed=12)), voice, background)

    assert verdict["e_o_locutor"] is False


def test_a_louder_recording_does_not_change_the_answer(modelo):
    """The editor raised the volume of their own sample before sending it.

    Level is not identity. Per-recording normalisation of the coefficients is
    what has to make this hold.
    """
    voice, background = modelo

    quiet = identify(features(_voice(RENAN, seconds=5.0, seed=13, gain=0.2)), voice, background)
    loud = identify(features(_voice(RENAN, seconds=5.0, seed=13, gain=1.0)), voice, background)

    assert quiet["e_o_locutor"] == loud["e_o_locutor"] is True


def test_too_little_speech_gets_no_verdict(modelo):
    """Not a false answer: no answer. A clip may not attribute speech on a guess."""
    voice, background = modelo

    verdict = identify(features(_voice(RENAN, seconds=0.3, seed=14)), voice, background)

    assert verdict["e_o_locutor"] is None
    assert "insuficiente" in verdict["motivo"]


def test_enrolment_refuses_a_sample_that_is_too_short():
    with pytest.raises(ValueError, match="quadros de fala"):
        enroll_from_features(features(_voice(RENAN, seconds=0.4, seed=15)), "renan")


def test_the_features_drop_silence():
    silence = np.zeros(SAMPLE_RATE * 3, dtype=np.float32)

    assert features(silence).shape[0] == 0


def test_a_background_needs_a_readable_source():
    assert background_from_source("/nao/existe.mp4", 0.0) is None

"""Test para validar o piso de densidade de fala (speech density floor).

DEFEITO CONFIRMADO: O corte 1 saiu 0-53s com 47s de silêncio + ~5.5s de fala = 89% mudo.
O energy_score com peso 0.15 não consegue vetar 89% de silêncio.

Este teste verifica que clips com baixa densidade de fala sejam rejeitados
pelo quality_gate quando o atributo speech_density está presente.
"""
import unittest
from modules.clip_selector import ClipSelector


class TestSpeechDensityFloor(unittest.TestCase):
    """Tests for speech density floor - rejecting mostly-silent clips."""

    def setUp(self):
        self.selector = ClipSelector()

    def test_low_speech_density_rejected(self):
        """Test that clips with speech density below 60% are rejected."""
        clip = {
            "duration": 60.0,
            "viral_score": 90,
            "has_hook": True,
            "context_complete": True,
            "payoff_complete": True,
            "speech_density": 0.08,  # 8% speech density
        }
        status = self.selector.quality_gate(clip)
        self.assertEqual(status[0], "reject")
        self.assertEqual(status[1], "low_speech_density")

    def test_good_speech_density_accepted(self):
        """Test that clips with good speech density (>= 60%) are NOT rejected for density."""
        clip = {
            "duration": 60.0,
            "viral_score": 90,
            "has_hook": True,
            "context_complete": True,
            "payoff_complete": True,
            "speech_density": 1.0,  # 100% speech density
        }
        status = self.selector.quality_gate(clip)
        self.assertNotEqual(status, ("reject", "low_speech_density"))


if __name__ == "__main__":
    unittest.main()

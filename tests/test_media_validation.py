import os
import unittest

from modules.media_validation import validate_media


FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_av.mp4")


@unittest.skipUnless(os.path.exists(FIXTURE), "fixture de mídia ainda não foi gerada")
class MediaValidationTests(unittest.TestCase):
    def test_validates_audio_video_fixture(self):
        result = validate_media(
            FIXTURE,
            expected_duration=2.0,
            duration_tolerance=0.25,
            expected_width=320,
            expected_height=180,
        )
        self.assertTrue(result.valid, result.as_dict())
        self.assertTrue(result.has_video)
        self.assertTrue(result.has_audio)
        self.assertEqual(result.width, 320)
        self.assertEqual(result.height, 180)

    def test_rejects_wrong_expected_duration(self):
        result = validate_media(FIXTURE, expected_duration=10.0, duration_tolerance=0.1)
        self.assertFalse(result.valid)
        self.assertTrue(any("Duração" in error for error in result.errors))


class MissingMediaTests(unittest.TestCase):
    def test_missing_file_is_invalid(self):
        result = validate_media("/tmp/furia-file-that-does-not-exist.mp4")
        self.assertFalse(result.valid)
        self.assertTrue(result.errors)


if __name__ == "__main__":
    unittest.main()

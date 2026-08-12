import unittest

from modules.timeline import TimelineMap


class TimelineMapTests(unittest.TestCase):
    def test_maps_derived_clip_back_to_original_after_removed_silence(self):
        timeline = TimelineMap.from_original_segments(
            [
                {"start": 0.0, "end": 5.0},
                {"start": 10.0, "end": 20.0},
            ]
        )

        # The second speech interval starts at 5s in the derived video but at
        # 10s in the original. This is the regression that the old pipeline
        # could get wrong when it cut the original with derived timestamps.
        mapped = timeline.derived_to_original(5.0, 8.0)
        self.assertEqual(mapped, [(10.0, 13.0)])

    def test_maps_interval_across_removed_silence_into_multiple_ranges(self):
        timeline = TimelineMap.from_original_segments(
            [
                {"start": 0.0, "end": 5.0},
                {"start": 10.0, "end": 20.0},
            ]
        )
        mapped = timeline.derived_to_original(4.0, 6.0)
        self.assertEqual(mapped, [(4.0, 5.0), (10.0, 11.0)])

    def test_round_trip_for_a_speech_interval(self):
        timeline = TimelineMap.from_original_segments(
            [
                {"start": 2.0, "end": 6.0},
                {"start": 9.0, "end": 13.0},
            ]
        )
        derived = timeline.original_to_derived(9.5, 11.0)
        self.assertEqual(derived, [(4.5, 6.0)])
        original = timeline.derived_to_original(*derived[0])
        self.assertEqual(original, [(9.5, 11.0)])

    def test_rejects_invalid_interval(self):
        timeline = TimelineMap.from_original_segments([{"start": 0, "end": 2}])
        with self.assertRaises(ValueError):
            timeline.derived_to_original(2, 1)


if __name__ == "__main__":
    unittest.main()

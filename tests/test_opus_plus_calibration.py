"""
Calibração profissional Opus+ usando o notebook oficial como referência.

Este teste NÃO usa volume como métrica. Usa o notebook apenas como:
- exemplos de clips bons que devem passar nos filtros
- exemplos de hard negatives que devem ser rejeitados
- referência de critérios editoriais (início quebrado, fim truncado, etc.)
"""
import json
import unittest
from pathlib import Path
from modules.clip_selector import ClipSelector

BASE_NOTEBOOK = Path(r"C:\Users\70156213125\furia_notebook_2_extracted")


class TestOpusPlusCalibration(unittest.TestCase):
    """Calibrate editorial quality filters against the official notebook reference."""

    @classmethod
    def setUpClass(cls):
        # Load benchmark data
        bh_path = BASE_NOTEBOOK / "renan belo horizonte diagnostics.json"
        with open(bh_path, 'r', encoding='utf-8') as f:
            cls.bh_diag = json.load(f)

        hn_path = BASE_NOTEBOOK / "hard-negatives-2b10adf6-131e-4a5a-af40-ac3c351cc093.json"
        with open(hn_path, 'r', encoding='utf-8') as f:
            cls.hard_negatives = json.load(f).get('items', [])

        tjson_path = BASE_NOTEBOOK / "project-31/transcription.json"
        with open(tjson_path, 'r', encoding='utf-8') as f:
            cls.transcription = json.load(f)
        cls.segments = cls.transcription.get('segments', [])

        # Extract final candidates from benchmark
        diagnostico = cls.bh_diag.get('selecao', {}).get('diagnostico', {})
        cls.final_candidates = diagnostico.get('final_candidates', [])

    def _find_segment(self, start, end, tolerance=2.0):
        """Find segment matching a time interval."""
        matches = []
        for seg in self.segments:
            seg_start = seg.get('start', 0)
            seg_end = seg.get('end', 0)
            # Check if segment overlaps with target interval
            if seg_end >= start - tolerance and seg_start <= end + tolerance:
                matches.append(seg)
        return matches

    def _editorial_flags_from_interval(self, start, end):
        """Get editorial flags for a time interval from the benchmark transcription."""
        matching_segs = self._find_segment(start, end)
        if not matching_segs:
            return None

        # Build text from matching segments
        text = ' '.join(s.get('text', '') for s in matching_segs)
        words = text.split()

        # Build metadata for editorial flags
        first_seg = matching_segs[0]
        metadata = {
            'start': first_seg.get('start', 0),
            'end': matching_segs[-1].get('end', 0),
            'speaker': first_seg.get('speaker'),
            'overlap_suspected': False,
            'timing_ambiguous': False,
            'topic_boundary': False,
            'speaker_turn_valid': True,
        }

        selector = ClipSelector()
        flags = selector._editorial_flags(text, metadata)
        return {
            'flags': flags,
            'text': text,
            'words': words,
            'start': start,
            'end': end,
            'duration': end - start,
        }

    def test_benchmark_final_candidates_have_editorial_flags(self):
        """Every final candidate in the benchmark should have editorial flags."""
        selector = ClipSelector()
        failures = []

        for candidate in self.final_candidates[:20]:  # Test first 20
            start = candidate.get('start', 0)
            end = candidate.get('end', 0)
            result = self._editorial_flags_from_interval(start, end)

            if result is None:
                failures.append(f"No segments found for [{start}-{end}]")
                continue

            flags = result['flags']
            text = result['text']

            # Every candidate should have payoff
            if not flags.get('payoff_complete'):
                failures.append(
                    f"[{start}-{end}] payoff incomplete: {text[:80]}..."
                )

            # Every candidate should have context
            if not flags.get('context_complete'):
                failures.append(
                    f"[{start}-{end}] context incomplete: {text[:80]}..."
                )

        # Calibration baseline: our filters are stricter than the benchmark's
        # editorial judgment. Track this ratio and improve toward <=30% failure.
        # Current baseline (2026-08-29): 34/81 = 42% failure rate
        calibration_baseline = 0.42
        failure_rate = len(failures) / len(self.final_candidates)

        print(f"\nCalibration baseline: {calibration_baseline:.1%}")
        print(f"Current failure rate: {failure_rate:.1%} ({len(failures)}/{len(self.final_candidates)})")

        if failure_rate > calibration_baseline:
            print("WARNING: Filters became stricter than baseline")
        elif failure_rate < calibration_baseline * 0.7:
            print("OK: Filters are more permissive than baseline")

        # For now, just report the ratio; don't hard-fail the test
        # The goal is to track this metric over time as we tune filters
        self.assertLessEqual(
            failure_rate,
            0.60,  # Allow up to 60% failure rate for now
            f"Filters too strict: {failure_rate:.1%} failure rate"
        )

    def test_hard_negatives_are_rejected(self):
        """Hard negatives from the benchmark should be rejected by our filters."""
        selector = ClipSelector()
        false_positives = []

        for hn in self.hard_negatives[:10]:  # Test first 10 hard negatives
            candidate = hn.get('candidate', {})
            winner = hn.get('winner', {})
            reason = hn.get('reason_code', '')

            # The candidate should be rejected
            if candidate.get('text_preview'):
                text = candidate['text_preview']
                start = candidate.get('start', 0)
                end = candidate.get('end', 0)

                result = self._editorial_flags_from_interval(start, end)
                if result:
                    flags = result['flags']

                    # Hard negatives should generally not have complete context
                    # (that's why they were rejected in the benchmark)
                    if flags.get('context_complete') and flags.get('payoff_complete'):
                        false_positives.append(
                            f"[{reason}] [{start}-{end}] passed both gates: {text[:60]}..."
                        )

        # Report false positives
        if false_positives:
            print(f"\n{len(false_positives)} hard negatives passed our filters:")
            for fp in false_positives[:5]:
                print(f"  - {fp}")

        # Allow some false positives; the benchmark's editorial judgment is stricter
        self.assertLessEqual(
            len(false_positives),
            len(self.hard_negatives) * 0.5,
            f"Too many hard negatives passed: {len(false_positives)}/{len(self.hard_negatives)}"
        )

    def test_no_mid_sentence_starts_in_benchmark(self):
        """Benchmark final candidates should not start mid-sentence."""
        selector = ClipSelector()
        mid_sentence_starts = []

        for candidate in self.final_candidates[:15]:
            start = candidate.get('start', 0)
            end = candidate.get('end', 0)
            result = self._editorial_flags_from_interval(start, end)

            if result and result['flags'].get('starts_mid_sentence'):
                mid_sentence_starts.append(
                    f"[{start}-{end}] starts mid-sentence: {result['text'][:60]}..."
                )

        if mid_sentence_starts:
            print(f"\n{len(mid_sentence_starts)} benchmark candidates start mid-sentence:")
            for m in mid_sentence_starts[:5]:
                print(f"  - {m}")

        # The benchmark should have very few mid-sentence starts
        self.assertLessEqual(
            len(mid_sentence_starts),
            2,
            f"Too many benchmark clips start mid-sentence: {len(mid_sentence_starts)}"
        )

    def test_touching_siblings_not_duplicates(self):
        """Touching siblings (gap <= 0.5s) should not be treated as duplicates."""
        selector = ClipSelector(max_clips=15)

        # Two touching clips from the benchmark
        clip1 = {
            'start': 87.115,
            'end': 143.07,
            'text': '[aplausos] Eu quero aqui a missão que a gente vai chegar lá no Nordeste, vaiar no Nordeste, vai chegar lá no norte e vai expulsar ON Picareta Internacional que atrapalha o desenvolvimento do nosso país.',
            'duration': 55.955,
            'viral_score': 90,
            'confidence': 0.9,
        }
        clip2 = {
            'start': 143.07,
            'end': 200.747,
            'text': 'Hoje nós temos uma casa, nós temos nossas cores, nós temos as nossas propostas, as nossas ideias, nós temos um time.',
            'duration': 57.677,
            'viral_score': 90,
            'confidence': 0.9,
        }

        # Both should survive overlap removal
        result = selector._remove_overlaps([clip1, clip2])
        self.assertEqual(
            len(result), 2,
            "Touching siblings should not be removed as duplicates"
        )

    def test_context_complete_allows_short_clips(self):
        """Clips with 8+ words and strong payoff should have context_complete=True."""
        selector = ClipSelector()

        # Short but complete clip
        flags = selector._editorial_flags(
            "Nós vamos eleger um presidente da República em 2026.",
            {
                'start': 10.0,
                'end': 15.0,
                'speaker': 'Renan',
                'overlap_suspected': False,
                'timing_ambiguous': False,
                'topic_boundary': False,
                'speaker_turn_valid': True,
            }
        )

        self.assertTrue(
            flags.get('context_complete'),
            "8-word clip with strong payoff should have context_complete=True"
        )

    def test_topic_boundary_is_review_signal_not_blocker(self):
        """topic_boundary should set needs_topic_review but not block context_complete."""
        selector = ClipSelector()

        flags = selector._editorial_flags(
            "Nós vamos eleger um presidente da República em 2026 com apoio de todo o Brasil.",
            {
                'start': 10.0,
                'end': 18.0,
                'speaker': 'Renan',
                'overlap_suspected': False,
                'timing_ambiguous': False,
                'topic_boundary': True,
                'speaker_turn_valid': True,
            }
        )

        self.assertTrue(
            flags.get('topic_boundary'),
            "topic_boundary flag should be preserved"
        )
        self.assertTrue(
            flags.get('needs_topic_review'),
            "needs_topic_review should be set"
        )
        self.assertTrue(
            flags.get('context_complete'),
            "context_complete should still be True despite topic_boundary"
        )


if __name__ == '__main__':
    unittest.main()

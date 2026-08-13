import unittest

from modules.daily_portfolio import build_daily_portfolio
from modules.editorial_ranker import EditorialRanker


class DailyPortfolioTests(unittest.TestCase):
    def _candidate(self, source, text, score=80, family="politico", **extra):
        return {
            "source_id": source,
            "start": extra.pop("start", 0),
            "end": extra.pop("end", 40),
            "duration": 40,
            "text": text,
            "editorial_potential_score": score,
            "confidence": 0.8,
            "editorial_family": family,
            "factors": {"context_completeness": 80, "completeness": 85, "clarity": 80},
            **extra,
        }

    def test_selects_global_portfolio_with_source_and_family_caps(self):
        candidates = []
        for source in ("live-a", "live-b", "live-c"):
            for index in range(5):
                candidates.append(self._candidate(source, f"Argumento específico {source} número {index}.", family="politico" if index % 2 == 0 else "humor"))
        result = build_daily_portfolio(candidates, target_min=6, max_clips=8, max_per_source=3, max_per_family=6)
        self.assertTrue(result["summary"]["target_met"])
        self.assertEqual(result["summary"]["selected_count"], 8)
        self.assertTrue(all(count <= 3 for count in result["summary"]["source_counts"].values()))

    def test_drops_duplicate_and_failed_gate(self):
        candidates = [
            self._candidate("live-a", "A mesma tese forte termina aqui.", score=90),
            self._candidate("live-b", "A mesma tese forte termina aqui.", score=89),
            self._candidate("live-c", "Isso sem antecedente", score=95, factors={"context_completeness": 30, "completeness": 40, "clarity": 80}),
        ]
        result = build_daily_portfolio(candidates, target_min=3, max_clips=5)
        self.assertEqual(result["summary"]["selected_count"], 1)
        self.assertGreaterEqual(result["summary"]["rejections"].get("duplicata_semantica", 0), 1)
        self.assertGreaterEqual(result["summary"]["rejections"].get("contexto_insuficiente", 0), 1)
        self.assertFalse(result["summary"]["target_met"])

    def test_ranker_exposes_global_portfolio_api(self):
        ranker = EditorialRanker()
        result = ranker.rank_daily_portfolio([
            self._candidate("live-a", "A proposta econômica termina com uma solução clara."),
            self._candidate("live-b", "Uma reação engraçada fecha com uma piada.", family="humor"),
        ], target_min=1, max_clips=2, min_score=55)
        self.assertIn("clips", result)
        self.assertIn("summary", result)
        self.assertEqual(result["summary"]["selected_count"], 2)


if __name__ == "__main__":
    unittest.main()

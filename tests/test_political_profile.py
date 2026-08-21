import unittest

from modules.political_profile import PROFILE_NAME, analyze_political_text
from modules.editorial_ranker import EditorialRanker


class PoliticalProfileTests(unittest.TestCase):
    def test_classifies_proposal_with_topic_and_specificity(self):
        text = (
            "O Brasil precisa reduzir os homicídios. Minha proposta é criar uma meta nacional "
            "com dados públicos e chegar a menos de 10 mil mortes por ano."
        )
        result = analyze_political_text(
            text,
            user_context="encontre propostas de segurança pública",
            channel_context="cortes políticos de Renan Santos e MBL",
        )
        self.assertEqual(result["editorial_type"], "proposta/programa")
        self.assertGreater(result["topic_relevance"], 50)
        self.assertGreater(result["proposal_strength"], 50)
        self.assertGreater(result["specificity"], 50)
        self.assertEqual(result["political_editorial_fit"], result["political_editorial_fit"])

    def test_detects_confrontation_and_evidence(self):
        result = analyze_political_text(
            "A decisão é ilegal e não se cumpre. O artigo 5 da Constituição protege essa liberdade.",
            user_context="encontre confrontos sobre o STF com base jurídica",
        )
        self.assertEqual(result["editorial_type"], "confronto/reacao")
        self.assertGreater(result["conflict_or_stakes"], 50)
        self.assertGreater(result["evidence_density"], 50)
        self.assertGreater(result["context_match"], 50)

    def test_flags_sensitive_named_allegations_without_blocking_candidate(self):
        result = analyze_political_text(
            "Flávio Bolsonaro cometeu crime de rachadinha e desviou dinheiro público.",
            user_context="encontre denúncias políticas",
        )
        self.assertTrue(result["needs_fact_review"])
        self.assertTrue(result["needs_legal_review"])
        self.assertGreater(result["sensitive_claim_hits"], 0)
        self.assertGreater(result["named_entity_count"], 0)

    def test_does_not_flag_plain_proposal_as_sensitive_allegation(self):
        result = analyze_political_text(
            "A proposta é criar uma meta pública de segurança e publicar os dados todos os meses."
        )
        self.assertFalse(result["needs_fact_review"])
        self.assertFalse(result["needs_legal_review"])

    def test_penalizes_unresolved_opening_context(self):
        resolved = analyze_political_text(
            "O STF publicou uma decisão ilegal e isso afeta a liberdade de expressão."
        )
        unresolved = analyze_political_text(
            "Isso é absurdo e ninguém explica o que aconteceu."
        )
        self.assertGreater(resolved["context_completeness"], unresolved["context_completeness"])

    def test_keeps_humor_as_non_political_family(self):
        result = analyze_political_text("KKKK lá ele! Renan ficou indignado e a plateia caiu na risada.")
        self.assertIn(result["editorial_family"], {"humor", "descontraido", "reacao"})
        self.assertIn("editorial_family_fit", result)
        self.assertNotEqual(result["editorial_family"], "politico")

    def test_distinguishes_central_comparative_and_lateral_entity_roles(self):
        central = analyze_political_text("O problema do governo Lula é a segurança pública e a proposta precisa mudar.")
        comparative = analyze_political_text("Enquanto Bolsonaro fala de ordem, Lula não apresenta uma proposta diferente.")
        lateral = analyze_political_text("Eu também encontrei Lula na feira ontem.")

        assert central["primary_entity_role"] == "central"
        assert central["entity_roles"]["lula"]["role"] == "central"
        assert comparative["primary_entity_role"] == "comparative"
        assert comparative["entity_roles"]["lula"]["role"] == "comparative"
        assert comparative["entity_roles"]["bolsonaro"]["role"] == "comparative"
        assert lateral["primary_entity_role"] == "lateral"
        assert lateral["entity_context_review_required"] is True

    def test_ranker_keeps_lateral_entity_review_bounded(self):
        ranker = EditorialRanker(editorial_profile=PROFILE_NAME)
        result = ranker.score_clip({
            "start": 0,
            "end": 35,
            "duration": 35,
            "text": "Eu também encontrei Lula na feira ontem.",
            "context_complete": True,
            "evidence_present": True,
            "payoff_complete": True,
        })

        assert result["primary_entity_role"] == "lateral"
        assert result["review_flags"]["entity_context_review_required"] is True
        assert result["technical_gate"]["entity_context_review_required"] is True
        assert "entidade citada lateralmente" in result["technical_gate"]["reasons"][-1]
        assert result["technical_gate"]["penalty"] <= 4

    def test_ranker_exposes_political_signals(self):
        ranker = EditorialRanker(
            channel_context="Canal político de Renan Santos e MBL",
            editorial_profile=PROFILE_NAME,
        )
        result = ranker.score_clip(
            {
                "start": 0,
                "end": 40,
                "duration": 40,
                "text": "Você sabia? O governo anunciou uma medida. A proposta é reduzir impostos e publicar os dados.",
            },
            user_context="encontre propostas econômicas com dados",
        )
        self.assertEqual(result["political_profile"], PROFILE_NAME)
        self.assertEqual(result["political_editorial_type"], "proposta/programa")
        self.assertIn("political_editorial_fit", result["factors"])
        self.assertIn("topic_relevance", result["political_signals"])
        self.assertGreater(result["editorial_potential_score"], 0)

    def test_ranker_exposes_editorial_family_for_reaction(self):
        ranker = EditorialRanker(editorial_profile=PROFILE_NAME)
        result = ranker.score_clip({"start": 0, "end": 35, "duration": 35, "text": "Ninguém esperava essa reação! Ele respondeu e deixou o estúdio em choque."})
        self.assertIn("editorial_family_fit", result["factors"])
        self.assertIn(result["political_signals"]["editorial_family"], {"reacao", "humor", "conversa"})
        self.assertGreater(result["editorial_potential_score"], 0)

    def test_ranker_exposes_sensitive_review_flags_separately_from_factors(self):
        ranker = EditorialRanker(editorial_profile=PROFILE_NAME)
        result = ranker.score_clip({
            "start": 0,
            "end": 35,
            "duration": 35,
            "text": "Flávio Bolsonaro cometeu crime de rachadinha e desviou dinheiro público.",
        })
        self.assertTrue(result["review_flags"]["needs_fact_review"])
        self.assertTrue(result["review_flags"]["needs_legal_review"])
        self.assertNotIn("needs_fact_review", result["factors"])
        self.assertNotIn("needs_legal_review", result["factors"])


    def test_sensitive_claim_without_context_or_evidence_enters_technical_review(self):
        ranker = EditorialRanker(editorial_profile=PROFILE_NAME)
        result = ranker.score_clip({
            "start": 0,
            "end": 35,
            "duration": 35,
            "text": "Flávio Bolsonaro cometeu crime e desviou dinheiro público.",
            "context_complete": False,
            "evidence_present": False,
            "payoff_complete": True,
        })
        self.assertGreaterEqual(result["technical_gate"]["penalty"], 10)
        self.assertIn("alegação sensível sem contexto ou evidência explícitos", result["technical_gate"]["reasons"])
        self.assertIn(result["technical_gate"]["status"], {"review", "weak"})


if __name__ == "__main__":
    unittest.main()

import unittest

from app.services.grok_reasoning import parse_reasoning


class GrokReasoningTests(unittest.TestCase):
    def test_accepts_schema_conformant_json(self) -> None:
        reasoning = parse_reasoning(
            '{"likely_cause":"Duplicate candidate payments","recommended_action":"Review both payment IDs",'
            '"confidence":0.8,"severity":"medium","requires_human_review":true,"evidence_refs":["pay_1","pay_2"]}'
        )
        self.assertEqual(reasoning.severity, "medium")

    def test_rejects_malformed_json(self) -> None:
        with self.assertRaises(RuntimeError):
            parse_reasoning('this is not JSON')


if __name__ == "__main__":
    unittest.main()

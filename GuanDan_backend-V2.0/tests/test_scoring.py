import unittest

from services.scoring import parse_score_value, build_score_update


class TestScoring(unittest.TestCase):
    def test_parse_score_value_valid(self):
        self.assertEqual(parse_score_value("2"), 2)
        self.assertEqual(parse_score_value(" 32 "), 32)

    def test_parse_score_value_invalid(self):
        self.assertIsNone(parse_score_value("1"))
        self.assertIsNone(parse_score_value("33"))
        self.assertIsNone(parse_score_value("abc"))
        self.assertIsNone(parse_score_value(None))

    def test_build_score_update_win(self):
        payload = build_score_update("A队", "B队", "14", "10", "")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["small_scores"]["A队"], 4)
        self.assertEqual(payload["small_scores"]["B队"], -4)
        self.assertEqual(payload["big_scores"]["A队"], 2)
        self.assertEqual(payload["big_scores"]["B队"], 0)

    def test_build_score_update_tie_requires_winner(self):
        payload = build_score_update("A队", "B队", "14", "14", "")
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "winner_required_when_tied")

    def test_build_score_update_tie_with_winner(self):
        payload = build_score_update("A队", "B队", "14", "14", "A队")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["big_scores"]["A队"], 2)
        self.assertEqual(payload["big_scores"]["B队"], 0)


if __name__ == "__main__":
    unittest.main()

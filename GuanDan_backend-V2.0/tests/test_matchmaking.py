import unittest
import random

from services.match_algorithm import generate_round_pairs


class TestMatchmaking(unittest.TestCase):
    def _sample_data(self):
        # 你可以按自己的赛制改这里：办公室、队名、队员、等级
        teams = [
            ("办1", "办1-A", "张三"),
            ("办2", "办2-A", "李四"),
            ("办3", "办3-A", "王五"),
            ("办4", "办4-A", "赵六"),
            ("办1", "办1-B", "甲"),
            ("办2", "办2-B", "乙"),
            ("办3", "办3-B", "丙"),
            ("办4", "办4-B", "丁"),
        ]
        team_levels = [
            ("办1-A", "A"),
            ("办2-A", "B"),
            ("办3-A", "C"),
            ("办4-A", "A"),
            ("办1-B", "B"),
            ("办2-B", "C"),
            ("办3-B", "A"),
            ("办4-B", "B"),
        ]
        return teams, team_levels

    def _generate_successful_result(self, rounds=3, max_retry=30):
        teams, team_levels = self._sample_data()
        last_result = None
        for seed in range(max_retry):
            random.seed(seed)
            result = generate_round_pairs(teams, team_levels, rounds=rounds)
            last_result = result
            if result["success"]:
                return result, teams
        self.fail(f"配对在 {max_retry} 次尝试后仍失败: {last_result.get('error') if last_result else 'unknown'}")

    def test_generate_round_pairs_success(self):
        result, teams = self._generate_successful_result(rounds=3)
        pairs = result["pairs"]
        self.assertEqual(len(pairs), (len(teams) // 2) * 3)

    def test_no_same_office_match(self):
        result, teams = self._generate_successful_result(rounds=3)
        office_by_team = {team_name: office for office, team_name, _ in teams}
        for team_a, team_b in result["pairs"]:
            self.assertNotEqual(office_by_team[team_a], office_by_team[team_b])

    def test_no_duplicate_pairs(self):
        result, _teams = self._generate_successful_result(rounds=3)
        seen = set()
        for pair in result["pairs"]:
            self.assertNotIn(pair, seen)
            seen.add(pair)


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from collections import Counter, defaultdict

from services.match_algorithm import (
    _calc_target_exposure,
    generate_round_pairs_large_scale,
)


def _build_sample_teams(team_count):
    ranks = ["青铜", "白银", "黄金"]
    teams = []
    levels = []
    for i in range(team_count):
        team_name = f"team_{i:04d}"
        teams.append((f"office_{i % 5}", team_name, f"member_{i:04d}"))
        levels.append((team_name, ranks[i % len(ranks)]))
    return teams, levels


def _pairs_by_round(pairs, team_count):
    tables_per_round = team_count // 2
    for i in range(0, len(pairs), tables_per_round):
        yield pairs[i : i + tables_per_round]


def _duplicate_ratio(pairs):
    seen = set()
    dup = 0
    for a, b in pairs:
        pair = tuple(sorted((a, b)))
        if pair in seen:
            dup += 1
        else:
            seen.add(pair)
    return dup / max(len(pairs), 1)


def _random_baseline_pairs(team_names, rounds, seed=0):
    import random

    rng = random.Random(seed)
    out = []
    for _ in range(rounds):
        current = list(team_names)
        rng.shuffle(current)
        for i in range(0, len(current) - 1, 2):
            out.append(tuple(sorted((current[i], current[i + 1]))))
    return out


class TestLargeScaleMatchmaking(unittest.TestCase):
    def test_basic_correctness(self):
        team_count = 60
        rounds = 5
        teams, levels = _build_sample_teams(team_count)
        result = generate_round_pairs_large_scale(
            teams, levels, rounds=rounds, seed=123, candidate_k=24
        )

        self.assertTrue(result["success"], msg=result["error"])
        self.assertEqual(len(result["pairs"]), (team_count // 2) * rounds)

        for one_round_pairs in _pairs_by_round(result["pairs"], team_count):
            used = []
            for a, b in one_round_pairs:
                used.extend([a, b])
            self.assertEqual(len(used), len(set(used)))

    def test_duplicate_rate_better_than_random_baseline(self):
        team_count = 90
        rounds = 6
        teams, levels = _build_sample_teams(team_count)

        result = generate_round_pairs_large_scale(
            teams, levels, rounds=rounds, seed=7, candidate_k=20
        )
        self.assertTrue(result["success"], msg=result["error"])

        algo_dup = _duplicate_ratio(result["pairs"])
        baseline = _random_baseline_pairs(
            [name for _, name, _ in teams],
            rounds=rounds,
            seed=7,
        )
        baseline_dup = _duplicate_ratio(baseline)

        self.assertLessEqual(algo_dup, baseline_dup)

    def test_rank_exposure_balance(self):
        team_count = 72
        rounds = 7
        teams, levels = _build_sample_teams(team_count)
        level_map = {t: lv for t, lv in levels}

        result = generate_round_pairs_large_scale(
            teams, levels, rounds=rounds, seed=999, candidate_k=24
        )
        self.assertTrue(result["success"], msg=result["error"])

        team_names = [name for _, name, _ in teams]
        target = _calc_target_exposure(team_names, level_map, rounds)
        exposure = {t: defaultdict(int) for t in team_names}

        for a, b in result["pairs"]:
            exposure[a][level_map[b]] += 1
            exposure[b][level_map[a]] += 1

        deviations = []
        for t in team_names:
            for rank in ("青铜", "白银", "黄金"):
                deviations.append(abs(exposure[t][rank] - target[t][rank]))

        avg_dev = sum(deviations) / max(len(deviations), 1)
        self.assertLessEqual(avg_dev, 1.4)

    def test_odd_team_bye_fairness(self):
        team_count = 31
        rounds = 7
        teams, levels = _build_sample_teams(team_count)

        result = generate_round_pairs_large_scale(
            teams, levels, rounds=rounds, seed=23, candidate_k=18
        )
        self.assertTrue(result["success"], msg=result["error"])
        self.assertEqual(len(result["pairs"]), (team_count // 2) * rounds)

        all_teams = {name for _, name, _ in teams}
        bye_counter = Counter()
        for one_round_pairs in _pairs_by_round(result["pairs"], team_count):
            used = set()
            for a, b in one_round_pairs:
                used.add(a)
                used.add(b)
            bye_teams = list(all_teams - used)
            self.assertEqual(len(bye_teams), 1)
            bye_counter[bye_teams[0]] += 1

        self.assertEqual(sum(bye_counter.values()), rounds)
        if bye_counter:
            self.assertLessEqual(max(bye_counter.values()) - min(bye_counter.values()), 1)

    def test_seed_reproducible(self):
        team_count = 40
        rounds = 4
        teams, levels = _build_sample_teams(team_count)

        result_a = generate_round_pairs_large_scale(
            teams, levels, rounds=rounds, seed=2026, candidate_k=16
        )
        result_b = generate_round_pairs_large_scale(
            teams, levels, rounds=rounds, seed=2026, candidate_k=16
        )
        result_c = generate_round_pairs_large_scale(
            teams, levels, rounds=rounds, seed=2027, candidate_k=16
        )

        self.assertTrue(result_a["success"], msg=result_a["error"])
        self.assertTrue(result_b["success"], msg=result_b["error"])
        self.assertTrue(result_c["success"], msg=result_c["error"])
        self.assertEqual(result_a["pairs"], result_b["pairs"])
        self.assertNotEqual(result_a["pairs"], result_c["pairs"])

    @unittest.skipUnless(
        os.getenv("RUN_LARGE_SMOKE") == "1",
        "Set RUN_LARGE_SMOKE=1 to enable 1000-team smoke test.",
    )
    def test_large_scale_smoke_1000(self):
        team_count = 1000
        rounds = 3
        teams, levels = _build_sample_teams(team_count)
        result = generate_round_pairs_large_scale(
            teams, levels, rounds=rounds, seed=100, candidate_k=24
        )
        self.assertTrue(result["success"], msg=result["error"])
        self.assertEqual(len(result["pairs"]), (team_count // 2) * rounds)


if __name__ == "__main__":
    unittest.main()

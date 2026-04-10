import random
from collections import defaultdict
from math import floor


def _standard_pair(team_a, team_b):
    """将两支队伍名标准化为有序元组，保证 (A, B) 与 (B, A) 等价。"""
    return tuple(sorted([team_a, team_b]))


def generate_round_pairs(teams, team_levels_list, rounds=3):
    """
    按轮次生成对阵结果。
    约束规则：
    1. 每轮每队只出现一次
    2. 同办公室不互打
    3. 同一对阵尽量不重复
    4. 优先匹配尚未交手过的等级组合
    """
    each_team_office = {}
    each_team_members = {}
    each_team = []
    teams_used_level = {}

    for office, team_name, member_name in teams:
        each_team_members[team_name] = member_name
        each_team_office[team_name] = office
        each_team.append(team_name)
        teams_used_level[team_name] = []

    each_team_level = {}
    for team_name, level in team_levels_list:
        each_team_level[team_name] = level

    all_pair = []
    all_used_pairs = set()

    for _ in range(rounds):
        round_pair = []
        one_round_used_teams = set()

        random.shuffle(each_team)
        other_each_team = each_team.copy()

        for team in each_team:
            if team in one_round_used_teams:
                continue

            matched = False
            random.shuffle(other_each_team)
            for other_team in other_each_team:
                if other_team in one_round_used_teams:
                    continue

                a, b = _standard_pair(team, other_team)
                if a == b or each_team_office[a] == each_team_office[b]:
                    continue
                if (a, b) in all_used_pairs:
                    continue
                if each_team_level[other_team] in teams_used_level[team]:
                    continue
                if each_team_level[team] in teams_used_level[other_team]:
                    continue

                matched = True
                teams_used_level[team].append(each_team_level[other_team])
                teams_used_level[other_team].append(each_team_level[team])
                one_round_used_teams.add(team)
                one_round_used_teams.add(other_team)
                round_pair.append((a, b))
                all_used_pairs.add((a, b))
                break

            # 放宽等级限制：只保留“不同办公室 + 不重复对阵”约束。
            if not matched:
                for other_team in each_team:
                    if other_team in one_round_used_teams:
                        continue

                    a, b = _standard_pair(team, other_team)
                    if a == b or each_team_office[a] == each_team_office[b]:
                        continue
                    if (a, b) in all_used_pairs:
                        continue

                    matched = True
                    teams_used_level[team].append(each_team_level[other_team])
                    teams_used_level[other_team].append(each_team_level[team])
                    one_round_used_teams.add(team)
                    one_round_used_teams.add(other_team)
                    round_pair.append((a, b))
                    all_used_pairs.add((a, b))
                    break

            if not matched:
                return {
                    "success": False,
                    "pairs": [],
                    "team_members": each_team_members,
                    "team_levels": each_team_level,
                    "error": "unable_to_match_all_teams",
                }

        all_pair.extend(round_pair)

    expected_len = (len(each_team) // 2) * rounds
    if len(all_pair) != expected_len:
        return {
            "success": False,
            "pairs": [],
            "team_members": each_team_members,
            "team_levels": each_team_level,
            "error": "pair_count_mismatch",
        }

    return {
        "success": True,
        "pairs": all_pair,
        "team_members": each_team_members,
        "team_levels": each_team_level,
        "error": None,
    }


def _build_team_maps(teams, team_levels_list):
    """
    将输入转换为统一的数据结构：
    - team_members: 队伍 -> 成员名（沿用旧接口字段）
    - team_levels: 队伍 -> 段位
    - all_teams: 去重后的队伍列表（稳定顺序）
    """
    team_members = {}
    all_teams = []
    seen = set()

    for row in teams:
        if len(row) < 3:
            return None, None, None, "invalid_team_row"
        team_name = row[1]
        member_name = row[2]
        team_members[team_name] = member_name
        if team_name not in seen:
            seen.add(team_name)
            all_teams.append(team_name)

    team_levels = {}
    for row in team_levels_list:
        if len(row) < 2:
            return None, None, None, "invalid_team_level_row"
        team_name, level = row[0], row[1]
        if team_name in seen:
            team_levels[team_name] = level

    for team_name in all_teams:
        if team_name not in team_levels:
            return None, None, None, "missing_team_level"

    return team_members, team_levels, all_teams, None


def _calc_target_exposure(all_teams, team_levels, rounds):
    """
    计算每支队伍在 rounds 轮内的“目标段位对手次数”。
    这里使用按对手池比例分配 + 最大余数法，保证每队配额和恰好为 rounds。
    """
    ranks = sorted(set(team_levels.values()))
    count_by_rank = defaultdict(int)
    for team in all_teams:
        count_by_rank[team_levels[team]] += 1

    target_exposure = {}
    for team in all_teams:
        my_rank = team_levels[team]
        opponent_total = max(len(all_teams) - 1, 1)

        raw = {}
        base = {}
        for rank in ranks:
            rank_pool = count_by_rank[rank] - (1 if rank == my_rank else 0)
            ratio = max(rank_pool, 0) / opponent_total
            expected = rounds * ratio
            raw[rank] = expected
            base[rank] = floor(expected)

        remaining = max(rounds - sum(base.values()), 0)
        order = sorted(
            ranks,
            key=lambda r: (raw[r] - base[r], r),
            reverse=True,
        )
        for i in range(remaining):
            base[order[i % len(order)]] += 1

        target_exposure[team] = base

    return target_exposure


def _pick_bye_team(active_teams, bye_count, rng):
    """
    奇数队时每轮需要 1 支队伍轮空。
    这里优先选择历史轮空次数最少的队伍，实现轮空均摊。
    """
    min_bye = min(bye_count[t] for t in active_teams)
    candidates = [t for t in active_teams if bye_count[t] == min_bye]
    return rng.choice(candidates)


def _edge_cost(
    team_a,
    team_b,
    *,
    team_levels,
    repeat_count,
    exposure,
    target_exposure,
    relax_level,
    rng,
):
    """
    对一条候选边打分（分值越小越优）。
    打分由以下项组成：
    - 重复对阵惩罚：避免 A-B 在多轮中重复
    - 配额偏差惩罚：尽量贴近每队的目标段位曝光
    - 同段位轻惩罚：鼓励跨段位，但不是硬约束
    - 微小随机扰动：打破完全同分，避免固定模式
    可通过调权重改变策略侧重点。
    """
    pair = _standard_pair(team_a, team_b)
    repeat_times = repeat_count[pair]
    if relax_level == 0 and repeat_times > 0:
        return None

    rank_a = team_levels[team_a]
    rank_b = team_levels[team_b]

    next_a_rank_b = exposure[team_a][rank_b] + 1
    next_b_rank_a = exposure[team_b][rank_a] + 1
    overflow_a = max(0, next_a_rank_b - target_exposure[team_a][rank_b])
    overflow_b = max(0, next_b_rank_a - target_exposure[team_b][rank_a])
    quota_overflow = overflow_a + overflow_b

    if relax_level == 0:
        w_repeat = 1000
    elif relax_level == 1:
        w_repeat = 350
    else:
        w_repeat = 150
    w_quota = 20
    w_same_rank = 5

    same_rank_penalty = 1 if rank_a == rank_b else 0
    jitter = rng.random() * 0.001

    return (
        repeat_times * w_repeat
        + quota_overflow * w_quota
        + same_rank_penalty * w_same_rank
        + jitter
    )


def _build_candidates_for_round(
    active_teams,
    *,
    team_levels,
    repeat_count,
    exposure,
    target_exposure,
    candidate_k,
    relax_level,
    rng,
):
    """
    为每支队伍构建稀疏候选集（最多 candidate_k 个）。
    这样能将匹配复杂度从全量 O(N^2) 降到更接近 O(N * candidate_k)。
    """
    candidate_k = max(int(candidate_k), 4)
    rank_buckets = defaultdict(list)
    for team in active_teams:
        rank_buckets[team_levels[team]].append(team)

    candidates = {}
    edge_cost_cache = {}

    all_ranks = sorted(rank_buckets.keys())
    for team in active_teams:
        picked = set()
        rank_preference = sorted(
            all_ranks,
            key=lambda r: (
                target_exposure[team][r] - exposure[team][r],
                rng.random(),
            ),
            reverse=True,
        )

        max_trials = candidate_k * 10
        trial = 0
        while len(picked) < candidate_k and trial < max_trials:
            rank = rank_preference[trial % len(rank_preference)]
            bucket = rank_buckets[rank]
            if bucket:
                other = rng.choice(bucket)
                if other != team and other not in picked:
                    cost = _edge_cost(
                        team,
                        other,
                        team_levels=team_levels,
                        repeat_count=repeat_count,
                        exposure=exposure,
                        target_exposure=target_exposure,
                        relax_level=relax_level,
                        rng=rng,
                    )
                    if cost is not None:
                        picked.add(other)
                        edge_cost_cache[_standard_pair(team, other)] = cost
            trial += 1

        if len(picked) < candidate_k:
            others = [o for o in active_teams if o != team and o not in picked]
            if others:
                sample_size = min(len(others), candidate_k * 2)
                for other in rng.sample(others, sample_size):
                    cost = _edge_cost(
                        team,
                        other,
                        team_levels=team_levels,
                        repeat_count=repeat_count,
                        exposure=exposure,
                        target_exposure=target_exposure,
                        relax_level=relax_level,
                        rng=rng,
                    )
                    if cost is None:
                        continue
                    picked.add(other)
                    edge_cost_cache[_standard_pair(team, other)] = cost
                    if len(picked) >= candidate_k:
                        break

        ordered = sorted(
            picked,
            key=lambda other: edge_cost_cache.get(_standard_pair(team, other), float("inf")),
        )
        candidates[team] = ordered

    return candidates, edge_cost_cache


def _greedy_match_round(active_teams, candidates, edge_cost_cache):
    """
    贪心构建一轮匹配：
    - 每次优先处理“可选对手最少”的队伍，减少后续死锁概率。
    """
    unmatched = set(active_teams)
    pairs = []

    while unmatched:
        team = min(
            unmatched,
            key=lambda t: sum(1 for o in candidates.get(t, []) if o in unmatched),
        )
        options = [o for o in candidates.get(team, []) if o in unmatched and o != team]
        if not options:
            break

        partner = min(
            options,
            key=lambda o: edge_cost_cache.get(_standard_pair(team, o), float("inf")),
        )

        unmatched.discard(team)
        unmatched.discard(partner)
        pairs.append(_standard_pair(team, partner))

    return pairs, unmatched


def _repair_unmatched(
    unmatched,
    pairs,
    *,
    team_levels,
    repeat_count,
    exposure,
    target_exposure,
    relax_level,
    max_repair_iter,
    rng,
):
    """
    对贪心残留未匹配队伍做局部修复。
    先尝试未匹配两两直连，再尝试与已有 pair 做 2-opt 交换。
    """
    unresolved = set(unmatched)
    cur_pairs = list(pairs)

    def cost(a, b):
        return _edge_cost(
            a,
            b,
            team_levels=team_levels,
            repeat_count=repeat_count,
            exposure=exposure,
            target_exposure=target_exposure,
            relax_level=relax_level,
            rng=rng,
        )

    for _ in range(max(0, int(max_repair_iter))):
        progress = False

        unresolved_list = list(unresolved)
        rng.shuffle(unresolved_list)
        used = set()
        for i, team_a in enumerate(unresolved_list):
            if team_a in used:
                continue
            for team_b in unresolved_list[i + 1:]:
                if team_b in used:
                    continue
                if cost(team_a, team_b) is None:
                    continue
                cur_pairs.append(_standard_pair(team_a, team_b))
                used.add(team_a)
                used.add(team_b)
                progress = True
                break
        unresolved.difference_update(used)
        if not unresolved:
            return cur_pairs, unresolved

        unresolved_list = list(unresolved)
        for team_u in unresolved_list:
            swapped = False
            for idx, (team_a, team_b) in enumerate(cur_pairs):
                if cost(team_u, team_a) is not None:
                    replacement = [x for x in unresolved if x != team_u and cost(x, team_b) is not None]
                    if replacement:
                        team_v = replacement[0]
                        cur_pairs[idx] = _standard_pair(team_u, team_a)
                        cur_pairs.append(_standard_pair(team_v, team_b))
                        unresolved.remove(team_u)
                        unresolved.remove(team_v)
                        progress = True
                        swapped = True
                        break
                if cost(team_u, team_b) is not None:
                    replacement = [x for x in unresolved if x != team_u and cost(x, team_a) is not None]
                    if replacement:
                        team_v = replacement[0]
                        cur_pairs[idx] = _standard_pair(team_u, team_b)
                        cur_pairs.append(_standard_pair(team_v, team_a))
                        unresolved.remove(team_u)
                        unresolved.remove(team_v)
                        progress = True
                        swapped = True
                        break
            if swapped and not unresolved:
                return cur_pairs, unresolved

        if not progress:
            break

    return cur_pairs, unresolved


def generate_round_pairs_large_scale(
    teams,
    team_levels_list,
    rounds=3,
    seed=None,
    candidate_k=30,
    max_repair_iter=3,
):
    """
    大规模队伍匹配算法（学习版）：
    1. 每轮每队最多参与一次；
    2. 多轮尽量减少重复对阵（分级放宽）；
    3. 段位对手分布尽量均衡（青铜/白银/黄金等通用）；
    4. 奇数队时轮空均摊。

    说明：在候选稀疏化前提下，整体复杂度近似 O(rounds * N * candidate_k)。
    """
    rng = random.Random(seed)

    team_members, team_levels, all_teams, err = _build_team_maps(teams, team_levels_list)
    if err:
        return {
            "success": False,
            "pairs": [],
            "team_members": team_members or {},
            "team_levels": team_levels or {},
            "error": err,
        }

    if rounds <= 0:
        return {
            "success": True,
            "pairs": [],
            "team_members": team_members,
            "team_levels": team_levels,
            "error": None,
        }

    ranks = sorted(set(team_levels.values()))
    target_exposure = _calc_target_exposure(all_teams, team_levels, rounds)

    repeat_count = defaultdict(int)
    exposure = {team: {rank: 0 for rank in ranks} for team in all_teams}
    bye_count = {team: 0 for team in all_teams}

    all_pairs = []
    is_odd = len(all_teams) % 2 == 1

    for _round_idx in range(rounds):
        active_teams = list(all_teams)
        if is_odd:
            bye_team = _pick_bye_team(active_teams, bye_count, rng)
            active_teams.remove(bye_team)
            bye_count[bye_team] += 1

        round_pairs = []
        round_unresolved = set(active_teams)

        for relax_level in (0, 1, 2):
            candidates, edge_cost_cache = _build_candidates_for_round(
                active_teams,
                team_levels=team_levels,
                repeat_count=repeat_count,
                exposure=exposure,
                target_exposure=target_exposure,
                candidate_k=candidate_k,
                relax_level=relax_level,
                rng=rng,
            )

            greedy_pairs, unresolved = _greedy_match_round(
                active_teams,
                candidates,
                edge_cost_cache,
            )
            if unresolved:
                greedy_pairs, unresolved = _repair_unmatched(
                    unresolved,
                    greedy_pairs,
                    team_levels=team_levels,
                    repeat_count=repeat_count,
                    exposure=exposure,
                    target_exposure=target_exposure,
                    relax_level=relax_level,
                    max_repair_iter=max_repair_iter,
                    rng=rng,
                )

            if not unresolved:
                round_pairs = greedy_pairs
                round_unresolved = set()
                break

            round_unresolved = unresolved

        if round_unresolved:
            return {
                "success": False,
                "pairs": [],
                "team_members": team_members,
                "team_levels": team_levels,
                "error": "unable_to_match_all_teams",
            }

        for team_a, team_b in round_pairs:
            pair = _standard_pair(team_a, team_b)
            repeat_count[pair] += 1
            exposure[team_a][team_levels[team_b]] += 1
            exposure[team_b][team_levels[team_a]] += 1

        all_pairs.extend(round_pairs)

    expected_len = (len(all_teams) // 2) * rounds
    if len(all_pairs) != expected_len:
        return {
            "success": False,
            "pairs": [],
            "team_members": team_members,
            "team_levels": team_levels,
            "error": "pair_count_mismatch",
        }

    return {
        "success": True,
        "pairs": all_pairs,
        "team_members": team_members,
        "team_levels": team_levels,
        "error": None,
    }

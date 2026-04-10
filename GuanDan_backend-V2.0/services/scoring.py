def parse_score_value(score):
    """将输入的等级文本转为整数，并限制在 2~32。"""
    try:
        value = int(str(score).strip())
    except (ValueError, TypeError):
        return None
    return value if 2 <= value <= 32 else None


def build_score_update(team1_name, team2_name, score_x_raw, score_y_raw, winner_raw):
    """
    写入操作，计算一场比赛的更新结果；
    返回 small_scores 与 big_scores，供路由层统一写库。
    """
    score_x = parse_score_value(score_x_raw)
    score_y = parse_score_value(score_y_raw)
    winner = str(winner_raw or "").strip().lower()
    team1 = str(team1_name).lower()
    team2 = str(team2_name).lower()

    if score_x is None or score_y is None:
        return {"ok": False, "error": "得分未输入"}

    if score_x == score_y and winner not in {team1, team2}:
        return {"ok": False, "error": "未选择最终局赢家"}

    small_scores = {
        team1_name: score_x - score_y,
        team2_name: score_y - score_x,
    }

    if score_x > score_y:
        big_scores = {team1_name: 2, team2_name: 0}
    elif score_y > score_x:
        big_scores = {team1_name: 0, team2_name: 2}
    else:
        if winner == team1:
            big_scores = {team1_name: 2, team2_name: 0}
        else:
            big_scores = {team1_name: 0, team2_name: 2}

    return {
        "ok": True,
        "error": None,
        "score_x": score_x,
        "score_y": score_y,
        "winner": winner,
        "small_scores": small_scores,
        "big_scores": big_scores,
    }

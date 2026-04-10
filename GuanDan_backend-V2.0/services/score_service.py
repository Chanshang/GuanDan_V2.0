def apply_score_update(get_db_connection, turn_num, small_scores, big_scores):
    """MySQL慢写入操作，按计算结果写入小分和大分。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for team_name, small_score in small_scores.items():
            cursor.execute(
                """
                UPDATE mini_team_info
                SET small_score = %s
                WHERE team_name = %s and turn = %s
                """,
                (small_score, team_name, turn_num),
            )

        for team_name, big_score in big_scores.items():
            cursor.execute(
                """
                UPDATE mini_team_info
                SET big_score = %s
                WHERE team_name = %s and turn = %s
                """,
                (big_score, team_name, turn_num),
            )

        conn.commit()
        return {"ok": True}
    except Exception as exc:
        conn.rollback()
        return {"ok": False, "error": str(exc)}
    finally:
        cursor.close()
        conn.close()


def apply_score_updates_batch(get_db_connection, updates):
    """
    Redis操作，批量写入比分更新（单事务）。
    updates 示例：
    [
      {"turn_num": 1, "small_scores": {"A队": 8}, "big_scores": {"A队": 2}},
      {"turn_num": 1, "small_scores": {"B队": 7}, "big_scores": {"B队": 0}},
    ]
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for item in updates:
            turn_num = int(item["turn_num"])
            small_scores = item.get("small_scores", {})
            big_scores = item.get("big_scores", {})

            for team_name, small_score in small_scores.items():
                cursor.execute(
                    """
                    UPDATE mini_team_info
                    SET small_score = %s
                    WHERE team_name = %s and turn = %s
                    """,
                    (small_score, team_name, turn_num),
                )

            for team_name, big_score in big_scores.items():
                cursor.execute(
                    """
                    UPDATE mini_team_info
                    SET big_score = %s
                    WHERE team_name = %s and turn = %s
                    """,
                    (big_score, team_name, turn_num),
                )

        conn.commit()
        return {"ok": True, "batch_count": len(updates)}
    except Exception as exc:
        conn.rollback()
        return {"ok": False, "error": str(exc), "batch_count": 0}
    finally:
        cursor.close()
        conn.close()

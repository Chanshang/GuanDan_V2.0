def fetch_match_generation_source(get_db_connection):
    """查询编排对阵需要的基础数据。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT office, team_name, member_name FROM mini_team_info WHERE turn = %s",
            (1,),
        )
        teams = cursor.fetchall()

        cursor.execute("SELECT team_name, level FROM team_level")
        team_levels_list = cursor.fetchall()
        return teams, team_levels_list
    finally:
        cursor.close()
        conn.close()


def replace_fight_info(get_db_connection, pairs, team_members, team_levels):
    """覆盖写入 fight_info 对阵表。"""
    total_tables = len(team_members) // 2
    if total_tables == 0:
        return {"ok": False, "error": "no_teams"}

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM fight_info")

        for idx, (team_name_1, team_name_2) in enumerate(pairs):
            member_name_1 = team_members[team_name_1]
            member_name_2 = team_members[team_name_2]
            round_num = idx // total_tables + 1

            cursor.execute(
                """
                INSERT INTO fight_info
                (id, team_name_1, members_1, team_name_2, members_2, turn, team_level_1, team_level_2)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    idx % total_tables + 1,
                    team_name_1,
                    member_name_1,
                    team_name_2,
                    member_name_2,
                    round_num,
                    team_levels[team_name_1],
                    team_levels[team_name_2],
                ),
            )

        conn.commit()
        return {"ok": True}
    except Exception as exc:
        conn.rollback()
        return {"ok": False, "error": str(exc)}
    finally:
        cursor.close()
        conn.close()


def fetch_all_fights(get_db_connection):
    """查询当前所有对阵记录。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM fight_info")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def fetch_all_fights_with_scores(get_db_connection):
    """查询后台管理对阵列表，并附带双方当前轮的大分/小分。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                f.id AS table_no,
                f.team_name_1,
                f.members_1,
                f.team_name_2,
                f.members_2,
                f.turn,
                f.team_level_1,
                f.team_level_2,
                t1.big_score AS team1_big_score,
                t1.small_score AS team1_small_score,
                t2.big_score AS team2_big_score,
                t2.small_score AS team2_small_score
            FROM fight_info f
            LEFT JOIN mini_team_info t1
              ON t1.team_name = f.team_name_1
             AND t1.turn = f.turn
            LEFT JOIN mini_team_info t2
              ON t2.team_name = f.team_name_2
             AND t2.turn = f.turn
            ORDER BY f.turn ASC, f.id ASC
            """
        )
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    finally:
        cursor.close()
        conn.close()


def fetch_fight_info_by_turn(get_db_connection, turn_num):
    """查询指定轮次桌号与对阵信息。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, team_name_1, members_1, team_name_2, members_2
            FROM fight_info
            WHERE turn = %s
            """,
            (turn_num,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

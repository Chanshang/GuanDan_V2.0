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

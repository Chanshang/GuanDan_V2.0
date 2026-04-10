def fetch_matches_by_turn(get_db_connection, turn):
    """查询指定轮次的对阵信息。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT *
            FROM fight_info
            WHERE turn = %s
            """,
            (int(turn),),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def fetch_scores_by_turn(get_db_connection, turn):
    """查询指定轮次每支队伍的小分信息。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT team_name, member_name, small_score
            FROM mini_team_info
            WHERE turn = %s
            """,
            (int(turn),),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def fetch_team_rankings(get_db_connection, turn):
    """查询队伍维度的当前轮与累计积分排名。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        turn_int = int(turn)
        cursor.execute(
            """
            SELECT
                ROW_NUMBER() OVER (ORDER BY SUM(big_score) DESC, SUM(small_score) DESC) AS rank_id,
                team_name,
                SUM(big_score) AS total_big_score,
                SUM(small_score) AS total_small_score
            FROM mini_team_info
            WHERE turn = %s
            GROUP BY team_name
            """,
            (turn_int,),
        )
        current_results = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                ROW_NUMBER() OVER (ORDER BY SUM(big_score) DESC, SUM(small_score) DESC) AS rank_id,
                team_name,
                SUM(big_score) AS total_big_score,
                SUM(small_score) AS total_small_score
            FROM mini_team_info
            WHERE turn <= %s
            GROUP BY team_name
            """,
            (turn_int,),
        )
        total_results = cursor.fetchall()
        return current_results, total_results
    finally:
        cursor.close()
        conn.close()


def fetch_office_rankings(get_db_connection, turn):
    """查询办公室维度的当前轮与累计积分排名。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        turn_int = int(turn)
        cursor.execute(
            """
            SELECT
                ROW_NUMBER() OVER (ORDER BY SUM(big_score) DESC, SUM(small_score) DESC) AS rank_id,
                office,
                SUM(big_score) AS total_big_score,
                SUM(small_score) AS total_small_score
            FROM mini_team_info
            WHERE turn = %s
            GROUP BY office
            """,
            (turn_int,),
        )
        current_results = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                ROW_NUMBER() OVER (ORDER BY SUM(big_score) DESC, SUM(small_score) DESC) AS rank_id,
                office,
                SUM(big_score) AS total_big_score,
                SUM(small_score) AS total_small_score
            FROM mini_team_info
            WHERE turn <= %s
            GROUP BY office
            """,
            (turn_int,),
        )
        total_results = cursor.fetchall()
        return current_results, total_results
    finally:
        cursor.close()
        conn.close()


def fetch_create_table_rows(get_db_connection):
    """查询展示页需要的队伍+桌号信息。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                m.*,
                f.id AS fight_id
            FROM mini_team_info m
            LEFT JOIN fight_info f
              ON (f.members_1 = m.member_name OR f.members_2 = m.member_name)
             AND f.turn = m.turn
            ORDER BY m.turn ASC, f.id ASC
            """
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def check_match_exists(get_db_connection, table_num, turn_num):
    """检查指定轮次和桌号是否存在对阵记录。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id
            FROM fight_info
            WHERE id = %s AND turn = %s
            """,
            (table_num, turn_num),
        )
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conn.close()

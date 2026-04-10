import openpyxl


def _normalize_member_text(value):
    """统一队员字段格式，便于后续匹配与展示。"""
    if not value:
        return value
    return (
        str(value)
        .replace(",", "-")
        .replace(" ", "")
        .replace("，", "-")
        .replace("、", "-")
    )


def import_registration_excel(filepath, get_db_connection):
    """
    导入报名 Excel，并初始化队伍、等级、轮次分数数据。
    返回值示例：
    {
        "ok": True,
        "imported_rows": 12,
    }
    """
    wb = openpyxl.load_workbook(filepath)
    sheet = wb.active

    conn = get_db_connection()
    cursor = conn.cursor()
    imported_rows = 0

    try:
        for row in sheet.iter_rows(min_row=3, values_only=True):
            if all(cell is None for cell in row):
                continue

            (
                team_id,
                office,
                captain,
                _team_name,
                team_name_1,
                team_level_1,
                members_1,
                team_name_2,
                team_level_2,
                members_2,
                team_name_3,
                team_level_3,
                members_3,
                team_name_4,
                team_level_4,
                members_4,
                substitute,
            ) = row[:17]

            if team_id is None:
                continue

            members_1 = _normalize_member_text(members_1)
            members_2 = _normalize_member_text(members_2)
            members_3 = _normalize_member_text(members_3)
            members_4 = _normalize_member_text(members_4)
            substitute = _normalize_member_text(substitute)

            cursor.execute(
                """
                INSERT INTO team_info (
                    id, office, captain,
                    team_name_1, members_1,
                    team_name_2, members_2,
                    team_name_3, members_3,
                    team_name_4, members_4, substitute
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    team_id,
                    office,
                    captain,
                    team_name_1,
                    members_1,
                    team_name_2,
                    members_2,
                    team_name_3,
                    members_3,
                    team_name_4,
                    members_4,
                    substitute,
                ),
            )

            team_names = [team_name_1, team_name_2, team_name_3, team_name_4]
            team_levels = [team_level_1, team_level_2, team_level_3, team_level_4]

            for name, level in zip(team_names, team_levels):
                cursor.execute(
                    "INSERT INTO team_level (team_name, level) VALUES (%s, %s)",
                    (name, level),
                )

            for turn in range(1, 4):
                if members_1 != "空":
                    cursor.execute(
                        """
                        INSERT INTO mini_team_info
                        (id, office, team_name, member_name, big_score, small_score, turn)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (team_id, office, team_name_1, members_1, 0, 0, turn),
                    )

                if members_2 != "空":
                    cursor.execute(
                        """
                        INSERT INTO mini_team_info
                        (id, office, team_name, member_name, big_score, small_score, turn)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (team_id, office, team_name_2, members_2, 0, 0, turn),
                    )

                if members_3 != "空":
                    cursor.execute(
                        """
                        INSERT INTO mini_team_info
                        (id, office, team_name, member_name, big_score, small_score, turn)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (team_id, office, team_name_3, members_3, 0, 0, turn),
                    )

                if members_4 != "空":
                    cursor.execute(
                        """
                        INSERT INTO mini_team_info
                        (id, office, team_name, member_name, big_score, small_score, turn)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (team_id, office, team_name_4, members_4, 0, 0, turn),
                    )

                cursor.execute(
                    """
                    INSERT INTO office_info (id, office, big_score, small_score, turn)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (team_id, office, 0, 0, turn),
                )

            imported_rows += 1

        conn.commit()
        return {"ok": True, "imported_rows": imported_rows}
    except Exception as exc:
        conn.rollback()
        return {"ok": False, "error": str(exc), "imported_rows": imported_rows}
    finally:
        cursor.close()
        conn.close()


def fetch_team_info_rows(get_db_connection):
    """查询 team_info 全表，用于首页展示。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM team_info")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

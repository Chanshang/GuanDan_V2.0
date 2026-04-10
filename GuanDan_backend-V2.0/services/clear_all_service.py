def clear_all_tables(get_db_connection):
    """清空比赛相关表，并返回执行结果。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("TRUNCATE TABLE mini_team_info")
        cursor.execute("TRUNCATE TABLE office_info")
        cursor.execute("TRUNCATE TABLE fight_info")
        cursor.execute("TRUNCATE TABLE team_info")
        cursor.execute("TRUNCATE TABLE team_level")
        conn.commit()
        return {"ok": True}
    except Exception as exc:
        conn.rollback()
        return {"ok": False, "error": str(exc)}
    finally:
        cursor.close()
        conn.close()

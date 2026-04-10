import os
from datetime import datetime


def save_score_log(turn, table_num, team1_name, team1_members, team2_name, team2_members, score_x, score_y):
    """记录每次录分操作，便于赛后追溯。"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = (
        f"Time: {current_time}\n"
        f"Turn: {turn}\n"
        f"Table: {table_num}\n"
        f"Team 1: {team1_name}\n"
        f"Members 1: {team1_members}\n"
        f"Team 1 Score: {score_x}\n"
        f"Team 2: {team2_name}\n"
        f"Members 2: {team2_members}\n"
        f"Team 2 Score: {score_y}\n"
        f"{'-' * 40}\n"
    )

    current_day = datetime.now().strftime('%Y-%m-%d')
    log_file_path = os.path.join(os.getcwd(), f'{current_day}_score_logs.txt')
    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write(log_entry)

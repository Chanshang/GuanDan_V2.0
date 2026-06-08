import argparse
from pathlib import Path

from services.registration_leveling import fill_registration_levels


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_REGISTRATION = BASE_DIR / "uploads" / "2026-GuanDan-list.xlsx"
DEFAULT_RANKING = BASE_DIR / "uploads" / "第四届中秋掼蛋最终排名表.xlsx"


def main():
    parser = argparse.ArgumentParser(
        description="根据上一届最终排名，为新一届报名表自动填写小组等级。"
    )
    parser.add_argument(
        "--registration",
        default=DEFAULT_REGISTRATION,
        type=Path,
        help="新报名表路径，默认读取 uploads/2026-GuanDan-list.xlsx",
    )
    parser.add_argument(
        "--ranking",
        default=DEFAULT_RANKING,
        type=Path,
        help="上一届最终排名表路径，默认读取 uploads/第四届中秋掼蛋最终排名表.xlsx",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="输出文件路径；不传时在报名表同目录生成“*-已填等级.xlsx”。",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="直接覆盖新报名表；默认不覆盖原表。",
    )
    args = parser.parse_args()

    output_path = args.registration if args.in_place else args.output
    result = fill_registration_levels(
        registration_path=args.registration,
        ranking_path=args.ranking,
        output_path=output_path,
    )

    print("已完成新报名表等级填充。")
    print(f"输出文件：{result['output_path']}")
    print(f"小队数量：{result['team_count']}")
    print(
        "等级数量："
        f"A={result['level_counts']['A']}，"
        f"B={result['level_counts']['B']}，"
        f"C={result['level_counts']['C']}"
    )
    print(f"上一届未匹配到的队员人次：{result['missing_member_count']}")
    if result["missing_members"]:
        preview = "、".join(result["missing_members"][:20])
        suffix = "……" if len(result["missing_members"]) > 20 else ""
        print(f"未匹配队员示例：{preview}{suffix}")


if __name__ == "__main__":
    main()

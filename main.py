import requests
import json
import sqlite3
import argparse
from pathlib import Path

DB_PATH = Path("drugs.db")
JSON_PATH = Path("4750.json")

URL = "https://wx.nhsa.gov.cn/nhsa/api/drug/getlist"

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Origin": "https://wx.nhsa.gov.cn",
    "Pragma": "no-cache",
    "Referer": "https://wx.nhsa.gov.cn/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "clientId": "",
    "remoteIp": "",
    "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "x_access_wxLogon": "%2Fpages%2FNRDL%2Findex%2Findex",
    "x_access_wxtoken": "",
}

COOKIES = {
    "acw_tc": "276082b217812343270776676ee83ec2fc1d50a2ef73d78880b7eb32b02797",
}


def fetch() -> dict:
    """从医保局 API 获取药品数据"""
    print("正在从医保局 API 获取药品数据...")
    response = requests.post(URL, headers=HEADERS, cookies=COOKIES, json={
        "name": "",
        "drugTypeId": "",
        "categoryId": "",
        "kind": "",
        "pageSize": 10000,
        "pageNum": 1,
        "id": "",
    })
    response.raise_for_status()
    data = response.json()

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total = data.get("data", {}).get("total", 0)
    print(f"获取成功，共 {total} 条药品，已保存到 {JSON_PATH}")
    return data


def import_db():
    """将 JSON 数据导入 SQLite"""
    if not JSON_PATH.exists():
        print(f"错误：找不到 {JSON_PATH}，请先运行 fetch 子命令")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS drugs (
            id INTEGER PRIMARY KEY,
            name TEXT,
            drug_type_id INTEGER,
            category_id INTEGER,
            kind INTEGER,
            kind_name TEXT,
            dosage_form TEXT,
            category_name TEXT,
            drug_type_name TEXT
        )
    """)

    # 清空旧数据
    cur.execute("DELETE FROM drugs")

    for item in data.get("data", {}).get("list", []):
        cur.execute("""
            INSERT OR REPLACE INTO drugs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["id"], item["name"], item["drugTypeId"], item["categoryId"],
            item["kind"], item.get("kindName"), item.get("dosageForm"),
            item.get("categoryName", ""), item.get("drugTypeName", "")
        ))

    conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM drugs").fetchone()[0]
    conn.close()
    print(f"导入成功，共 {count} 条药品，已保存到 {DB_PATH}")


def main():
    parser = argparse.ArgumentParser(description="GoodYeah - 医保药品目录工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    subparsers.add_parser("fetch", help="从医保局 API 获取药品数据")

    subparsers.add_parser("import", help="将 JSON 数据导入 drugs.db")

    update_parser = subparsers.add_parser("update", help="一键更新（fetch + import）")

    args = parser.parse_args()

    if args.command == "fetch":
        fetch()
    elif args.command == "import":
        import_db()
    elif args.command == "update":
        fetch()
        import_db()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
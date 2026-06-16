"""
医保耗材标准编码全量数据抓取脚本

用法:
  uv run python fetch_std_drugs.py run       # 从当前 checkpoint 继续运行
  uv run python fetch_std_drugs.py reset     # 从第 1 页重新开始
  uv run python fetch_std_drugs.py test     # 测试第 1 页，查看字段
"""

import requests
import json
import sqlite3
import time
import random
import os
import sys
from pathlib import Path
from tqdm import tqdm

# ========== 配置区 ==========
SUPPLIES_PREFIX = "supplies"
CHECKPOINT_FILE = Path(".fetch_checkpoint")
MAX_ROWS_PER_PAGE = 1000
# ===========================

URL = "https://code.nhsa.gov.cn/hc/stdPublishData/getStdPublicDataList1.html"

HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://code.nhsa.gov.cn",
    "Pragma": "no-cache",
    "Referer": "https://code.nhsa.gov.cn/hc/stdPublishData/toQueryStdPublicDataList.html?releaseVersion=20260427?batchNumber=20260427",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
}

# 手动维护 Cookie（过期后替换）
COOKIES = {
    "pageSelect": "c21ff3e4dc72e763ea75188fa39e0677=2",
    "queryCondition": "ab52740b81ca306f0138d92ebc41cf9f%3D%7B%22releaseVersion%22%3A%2220260427%22%2C%22releaseVersion2%22%3A%2220260427%3FbatchNumber%3D20260427%22%2C%22specificationCode%22%3A%22%22%2C%22commonname%22%3A%22%22%2C%22companyName%22%3A%22%22%2C%22catalogname1%22%3A%22%22%2C%22catalogname2%22%3A%22%22%2C%22catalogname3%22%3A%22%22%2C%22genericname%22%3A%22%22%7D",
}


def load_checkpoint() -> int:
    """读取当前页码，未找到则返回 1"""
    if not CHECKPOINT_FILE.exists():
        return 1
    try:
        page = int(CHECKPOINT_FILE.read_text().strip())
        print(f"[Checkpoint] 从第 {page} 页继续")
        return page
    except:
        return 1


def save_checkpoint(page: int):
    """保存当前页码"""
    CHECKPOINT_FILE.write_text(str(page))


def init_db():
    """初始化数据库表"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS drugs (
            specificationcode TEXT UNIQUE,
            commonname TEXT,
            companyname TEXT,
            catalogname1 TEXT,
            catalogname2 TEXT,
            catalogname3 TEXT,
            genericname TEXT,
            mediclevel TEXT,
            isimported TEXT,
            isreimbursed TEXT,
            reimbursementratio TEXT,
            formularytype TEXT,
            hospitallevel TEXT,
            remark TEXT,
            auditdate TEXT,
            releaseversion TEXT,
            releaseversion2 TEXT,
            PRIMARY KEY (specificationcode)
        )
    """)
    conn.commit()
    conn.close()


def get_existing_count() -> int:
    """获取数据库已有条数"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM drugs")
    count = cur.fetchone()[0]
    conn.close()
    return count


def fetch_page(session: requests.Session, page: int) -> dict:
    """请求单页数据"""
    data = {
        "releaseVersion": "20260427",
        "releaseVersion2": "20260427?batchNumber=20260427",
        "specificationCode": "",
        "commonname": "",
        "companyName": "",
        "catalogname1": "",
        "catalogname2": "",
        "catalogname3": "",
        "genericname": "",
        "_search": "false",
        "nd": str(int(time.time() * 1000)),
        "rows": MAX_ROWS_PER_PAGE,
        "page": page,
        "sidx": "",
        "sord": "asc",
    }
    response = session.post(URL, headers=HEADERS, cookies=COOKIES, data=data, timeout=30)
    response.raise_for_status()
    return response.json()


def write_rows(rows: list):
    """批量写入 SQLite"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for row in rows:
        cur.execute("""
            INSERT OR REPLACE INTO drugs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.get("specificationCode", ""),
            row.get("commonname", ""),
            row.get("companyName", ""),
            row.get("catalogname1", ""),
            row.get("catalogname2", ""),
            row.get("catalogname3", ""),
            row.get("genericname", ""),
            row.get("mediclevel", ""),
            row.get("isimported", ""),
            row.get("isreimbursed", ""),
            row.get("reimbursementratio", ""),
            row.get("formularytype", ""),
            row.get("hospitallevel", ""),
            row.get("remark", ""),
            row.get("auditdate", ""),
            row.get("releaseVersion", ""),
            row.get("releaseVersion2", ""),
        ))

    conn.commit()
    conn.close()


def run():
    """主循环：分页抓取 + 增量写入"""
    # 使用 Session 复用 TCP 连接
    session = requests.Session()

    # 先获取 JSESSIONID
    session.post("https://code.nhsa.gov.cn/hc/stdPublishData/getPublishGgxhCountByCondition1.html",
                 headers=HEADERS, cookies=COOKIES,
                 data={"releaseVersion": "20260427", "specificationCode": ""}, timeout=30)

    # 先请求第一页获取 releaseVersion 和 records
    result = fetch_page(session, 1)
    release_version = result.get("rows", [{}])[0].get("releaseVersion", "unknown")
    total_estimated = result.get("records", 0)

    global DB_PATH, CHECKPOINT_FILE
    DB_PATH = Path(f"{SUPPLIES_PREFIX}_{release_version}.db")
    CHECKPOINT_FILE = Path(f".fetch_checkpoint_{release_version}")

    init_db()

    current_page = load_checkpoint()
    consecutive_errors = 0

    existing_count = get_existing_count()
    print(f"[Start] 总计 {total_estimated:,} 条，已有 {existing_count:,} 条，每页 {MAX_ROWS_PER_PAGE} 条")
    print("[Ctrl+C] 中途退出可在恢复时从 checkpoint 继续\n")

    try:
        pbar = tqdm(total=total_estimated, initial=existing_count, unit="条", desc="抓取进度")
        pbar.update(existing_count)

        # 写入第一页（已抓取）
        rows = result.get("rows", [])
        if rows:
            write_rows(rows)
            pbar.update(len(rows))
            current_count = get_existing_count()
            pbar.set_postfix_str(f"DB: {current_count:,} 条")

        current_page = 2  # 下一页从 2 开始

        while True:
            try:
                result = fetch_page(session, current_page)
            except Exception as e:
                consecutive_errors += 1
                print(f"\n[Error] 第 {current_page} 页请求失败: {e}")
                if consecutive_errors >= 5:
                    print("[Fatal] 连续 5 次失败，可能 Cookie 已过期")
                    raise
                wait = random.uniform(3, 8)
                print(f"[Retry] {wait:.1f}s 后重试...")
                time.sleep(wait)
                continue

            consecutive_errors = 0
            rows = result.get("rows", [])

            if not rows:
                print(f"\n[Done] 已抓取完毕，共 {get_existing_count():,} 条")
                if CHECKPOINT_FILE.exists():
                    CHECKPOINT_FILE.unlink()
                break

            write_rows(rows)
            current_count = get_existing_count()
            pbar.set_postfix_str(f"DB: {current_count:,} 条")
            pbar.update(current_count - pbar.n)

            # 已达总数，主动结束
            if pbar.n >= pbar.total:
                print(f"\n[Done] 已抓取完毕，共 {current_count:,} 条")
                if CHECKPOINT_FILE.exists():
                    CHECKPOINT_FILE.unlink()
                break

            # 写入成功后更新 checkpoint（不超过最大页数）
            max_page = (pbar.total + MAX_ROWS_PER_PAGE - 1) // MAX_ROWS_PER_PAGE
            save_checkpoint(min(current_page + 1, max_page + 1))

            current_page += 1

            # 随机延迟 0.5~2s
            time.sleep(random.uniform(0.5, 2.0))

        pbar.close()

    except KeyboardInterrupt:
        pbar.close()
        print(f"\n[Interrupt] 已暂停，下次运行自动从第 {current_page} 页继续")
        save_checkpoint(current_page)


def test_first_page():
    """测试第 1 页，查看字段和样本数据"""
    print("[Test] 请求第 1 页...\n")
    try:
        session = requests.Session()
        result = fetch_page(session, 1)
        total = result.get("total", 0)
        rows = result.get("rows", [])
        print(f"total: {total:,}")
        print(f"本页返回: {len(rows)} 条\n")

        if rows:
            print("字段列表:")
            for key in rows[0].keys():
                print(f"  - {key}")
            print("\n第一条数据样本:")
            print(json.dumps(rows[0], ensure_ascii=False, indent=2))
        else:
            print("无数据，请检查 Cookie 是否有效")

    except Exception as e:
        print(f"[Error] {e}")
        print("Cookie 可能已过期，请更新 Cookie")


def reset():
    """重置 checkpoint，重新开始"""
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
    print("[Reset] 已重置，从第 1 页开始")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "run":
        run()
    elif cmd == "test":
        init_db()
        test_first_page()
    elif cmd == "reset":
        reset()
    else:
        print(__doc__)
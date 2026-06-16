"""
医保耗材规格型号详情抓取脚本

根据 supplies.db 中的 specificationCode，逐个抓取其规格型号详情。

用法:
  uv run python fetch_std_details.py run       # 从 checkpoint 继续
  uv run python fetch_std_details.py reset     # 从头开始
  uv run python fetch_std_details.py test      # 测试单个 specificationCode
"""

import requests
import json
import sqlite3
import time
import random
import sys
from pathlib import Path
from tqdm import tqdm
import ddddocr

# ========== 配置区 ==========
SUPPLIES_DB = Path("supplies_20260427.db")
DETAIL_DB = Path("supply_details.db")
CHECKPOINT_FILE = Path(".detail_checkpoint")
MAX_ROWS_PER_PAGE = 25
# ===========================

URL = "https://code.nhsa.gov.cn/hc/stdPublishData/getStdPublicDataListDetail1.html"

HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://code.nhsa.gov.cn",
    "Pragma": "no-cache",
    "Referer": "https://code.nhsa.gov.cn/hc/stdPublishData/toPublicDetailDialog1.html",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
}

COOKIES = {
    "pageSelect": "c21ff3e4dc72e763ea75188fa39e0677=2204",
    "queryCondition": "4dc997228c8da1241bcf91c92f5a5657%3D%7B%22specificationCode%22%3A%22%22%2C%22releaseVersion%22%3A%2220260427%22%7D",
}


def load_checkpoint() -> int:
    if not CHECKPOINT_FILE.exists():
        return 0
    try:
        return int(CHECKPOINT_FILE.read_text().strip())
    except:
        return 0


def save_checkpoint(idx: int):
    CHECKPOINT_FILE.write_text(str(idx))


def get_all_specification_codes() -> list:
    conn = sqlite3.connect(SUPPLIES_DB)
    cur = conn.cursor()
    cur.execute("SELECT specificationcode FROM drugs ORDER BY specificationcode")
    codes = [row[0] for row in cur.fetchall()]
    conn.close()
    return codes


def init_db():
    conn = sqlite3.connect(DETAIL_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS supply_details (
            id TEXT PRIMARY KEY,
            specificationcode TEXT,
            registrant TEXT,
            catalogname1 TEXT,
            catalogname2 TEXT,
            catalogname3 TEXT,
            commonname TEXT,
            matrial TEXT,
            characteristic TEXT,
            regcardnm TEXT,
            regdSt TEXT,
            regdEd TEXT,
            oldRegcardNm TEXT,
            regcardName TEXT,
            productName TEXT,
            unit TEXT,
            companyName TEXT,
            businessLicense TEXT,
            releaseVersion TEXT,
            ggxhCount TEXT,
            specification TEXT,
            model TEXT,
            udiCode TEXT,
            codeCount TEXT,
            dataResource TEXT,
            genericnumber TEXT,
            genericname TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_spec ON supply_details(specificationcode)")
    conn.commit()
    conn.close()
    print(f"[DB] 已初始化 {DETAIL_DB}")


def get_existing_count() -> int:
    conn = sqlite3.connect(DETAIL_DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT specificationcode) FROM supply_details")
    count = cur.fetchone()[0]
    conn.close()
    return count


def write_rows(rows: list):
    conn = sqlite3.connect(DETAIL_DB)
    cur = conn.cursor()
    for row in rows:
        cur.execute("""
            INSERT OR IGNORE INTO supply_details VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.get("id", ""),
            row.get("specificationCode", ""),
            row.get("registrant", ""),
            row.get("catalogname1", ""),
            row.get("catalogname2", ""),
            row.get("catalogname3", ""),
            row.get("commonname", ""),
            row.get("matrial", ""),
            row.get("characteristic", ""),
            row.get("regcardnm", ""),
            row.get("regdSt", ""),
            row.get("regdEd", ""),
            row.get("oldRegcardNm", ""),
            row.get("regcardName", ""),
            row.get("productName", ""),
            row.get("unit", ""),
            row.get("companyName", ""),
            row.get("businessLicense", ""),
            row.get("releaseVersion", ""),
            row.get("ggxhCount", ""),
            row.get("specification", ""),
            row.get("model", ""),
            row.get("udiCode", ""),
            row.get("codeCount", ""),
            row.get("dataResource", ""),
            row.get("genericnumber", ""),
            row.get("genericname", ""),
        ))
    conn.commit()
    conn.close()


def fetch_detail(session: requests.Session, specificationCode: str, releaseVersion: str = "20260427") -> dict:
    data = {
        "specificationCode": specificationCode,
        "releaseVersion": releaseVersion,
        "_search": "false",
        "nd": str(int(time.time() * 1000)),
        "rows": MAX_ROWS_PER_PAGE,
        "page": 1,
        "sidx": "",
        "sord": "asc",
    }
    response = session.post(URL, headers=HEADERS, cookies=COOKIES, data=data, timeout=30)
    response.raise_for_status()
    return response.json()


def verify_captcha(session: requests.Session, code: str) -> bool:
    verify_url = "https://code.nhsa.gov.cn/hc/veryIpCode"
    params = {"vyCode": code}
    response = session.get(verify_url, headers=HEADERS, params=params, timeout=10)
    return response.text.strip() == "succ"


def get_captcha_img(session: requests.Session) -> bytes:
    captcha_url = "https://code.nhsa.gov.cn/hc/ipActuatorVeryCode"
    response = session.get(captcha_url, headers=HEADERS, timeout=10)
    return response.content


def recognize_captcha(ocr, img_bytes: bytes) -> str:
    return ocr.classification(img_bytes)


def handle_captcha(ocr, session: requests.Session) -> bool:
    for attempt in range(3):
        captcha_img = get_captcha_img(session)
        code = recognize_captcha(ocr, captcha_img)
        print(f"[Captcha] OCR: {code}", end=" ")
        if verify_captcha(session, code):
            print("验证通过")
            return True
        print("失败，重试...")
    with open(".captcha.png", "wb") as f:
        f.write(captcha_img)
    print("[Captcha] 已保存到 .captcha.png，请手动输入：")
    code = input("验证码: ").strip()
    if not verify_captcha(session, code):
        print("[Error] 验证码错误")
        return False
    print("[Captcha] 验证通过")
    return True


def run():
    init_db()

    codes = get_all_specification_codes()
    total_codes = len(codes)
    print(f"[Total] 共 {total_codes:,} 个 specificationCode 待抓取\n")

    ocr = ddddocr.DdddOcr()

    session = requests.Session()
    session.post("https://code.nhsa.gov.cn/hc/stdPublishData/getPublishGgxhCountByCondition1.html",
                 headers=HEADERS, cookies=COOKIES,
                 data={"releaseVersion": "20260427", "specificationCode": ""}, timeout=30)
    jsessionid = session.cookies.get("JSESSIONID")
    if jsessionid:
        print(f"[Cookie] JSESSIONID: {jsessionid}")

    # 检测是否需要验证码
    try:
        test_result = fetch_detail(session, "C0101010011303807555")
    except Exception as e:
        if "405" in str(e):
            print(f"[Error] 初始化请求被限流 (405)，请等待几分钟后重试")
            return
        raise
    if isinstance(test_result.get("rows"), str) and "veryScripts" in test_result.get("rows", ""):
        print("[Captcha] 需要验证码，尝试 OCR...")
        if not handle_captcha(ocr, session):
            return
        jsessionid = session.cookies.get("JSESSIONID")

    start_idx = load_checkpoint()
    details_fetched = 0

    print(f"[Start] 从第 {start_idx} 个继续（已抓取 {get_existing_count():,} 个）\n")

    try:
        pbar = tqdm(total=total_codes, initial=start_idx, unit="个", desc="抓取详情")

        for i in range(start_idx, total_codes):
            spec_code = codes[i]

            try:
                result = fetch_detail(session, spec_code)

                if isinstance(result.get("rows"), str) and "veryScripts" in str(result.get("rows", "")):
                    print(f"\n[Captcha] 第 {i+1}/{total_codes} 遇到验证码...")
                    if not handle_captcha(ocr, session):
                        return
                    jsessionid = session.cookies.get("JSESSIONID")
                    result = fetch_detail(session, spec_code)

            except Exception as e:
                err_str = str(e)
                if "405" in err_str:
                    print(f"\n[Error] 第 {i+1}/{total_codes} {spec_code} 405，等待 60s 重试...")
                    time.sleep(60)
                    # 405 不保存 checkpoint，不 update pbar，重试当前
                    continue
                else:
                    print(f"\n[Error] 第 {i+1}/{total_codes} {spec_code} 请求失败: {e}")
                    time.sleep(random.uniform(3, 8))
                    continue

            rows = result.get("rows", [])
            if rows:
                write_rows(rows)
                details_fetched += len(rows)
                pbar.set_postfix_str(f"详情: {details_fetched:,} 条")

            pbar.update(1)
            save_checkpoint(i + 1)

            time.sleep(random.uniform(0.3, 1.0))

        pbar.close()
        print(f"\n[Done] 完成，共处理 {total_codes} 个 specificationCode，{details_fetched} 条详情")
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()

    except KeyboardInterrupt:
        print(f"\n[Interrupt] 已暂停，下次运行自动从第 {i} 个继续")
        save_checkpoint(i)


def test_one():
    print("[Test] 请求示例...\n")
    try:
        session = requests.Session()
        result = fetch_detail(session, "C0101010011303807555")
        rows = result.get("rows", [])
        print(f"返回条数: {len(rows)}\n")
        if rows:
            print("字段列表:")
            for key in rows[0].keys():
                print(f"  - {key}")
            print("\n第一条数据样本:")
            print(json.dumps(rows[0], ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[Error] {e}")


def reset():
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
    print("[Reset] 已重置")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "run":
        run()
    elif cmd == "test":
        test_one()
    elif cmd == "reset":
        reset()
    else:
        print(__doc__)
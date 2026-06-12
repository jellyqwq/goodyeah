import sqlite3
import json

with open("4750.json", "r", encoding="utf-8") as f:
    data = json.load(f)

conn = sqlite3.connect("drugs.db")
cur = conn.cursor()

# 创建表
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

# 批量插入
for item in data["data"]["list"]:
    cur.execute("""
        INSERT OR REPLACE INTO drugs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item["id"], item["name"], item["drugTypeId"], item["categoryId"],
        item["kind"], item["kindName"], item["dosageForm"],
        item.get("categoryName", ""), item["drugTypeName"]
    ))

conn.commit()
conn.close()
print("已保存到 drugs.db")

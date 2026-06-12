import sqlite3

# 查询示例：按名称模糊搜索
conn = sqlite3.connect("drugs.db")
cur = conn.cursor()
# cur.execute("SELECT name, kind_name FROM drugs WHERE name LIKE '%阿司匹林%'")
cur.execute("SELECT name, kind_name FROM drugs")
print(cur.fetchall())
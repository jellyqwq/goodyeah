# GoodYeah

国家医保药品目录查询工具，支持症状问诊和药品推荐。

## 项目结构

```
goodyeah/
├── drugs.db                    # SQLite 数据库，包含 4750 条医保药品数据
├── 4750.json                  # 原始 API 响应数据
├── import_to_sqlite.py         # 将 JSON 导入数据库脚本
├── getlist.py                 # 请求医保药品列表 API 脚本
├── main.py                    # 项目入口
├── pyproject.toml             # Python 依赖配置
├── 药品目录凡例.md            # 《药品目录》凡例（政策说明文档）
├── .claude/
│   └── skills/
│       ├── doctor_yeah.md     # 医生好耶技能（西药、只开医保药）
│       └── doctor_soyo.md     # 医生 Soyo 技能（中西药皆可、询问患者偏好）
└── .venv/                     # uv 虚拟环境
```

## 快速开始

### 环境安装

```bash
# 项目使用 uv 管理 Python 环境
uv sync

# 激活虚拟环境
source .venv/bin/activate
```

### 数据更新

从医保局 API 获取最新药品数据：

```bash
uv run python getlist.py
```

将 JSON 数据导入 SQLite：

```bash
uv run python import_to_sqlite.py
```

### 查询药品

```bash
# 模糊搜索药品名
uv run python -c "
import sqlite3
conn = sqlite3.connect('drugs.db')
cur = conn.cursor()
cur.execute(\"SELECT name, kind_name, dosage_form FROM drugs WHERE name LIKE '%布洛芬%'\")
for row in cur.fetchall():
    print(row)
"

# 查看所有药品类型
uv run python -c "
import sqlite3
conn = sqlite3.connect('drugs.db')
cur = conn.cursor()
cur.execute('SELECT DISTINCT drug_type_name FROM drugs')
print(cur.fetchall())
"
```

## 数据库表结构

```sql
CREATE TABLE drugs (
    id INTEGER PRIMARY KEY,
    name TEXT,                 -- 药品名称
    drug_type_id INTEGER,      -- 药品类型ID
    category_id INTEGER,      -- 分类ID
    kind INTEGER,              -- 医保类型（1=甲类，2=乙类）
    kind_name TEXT,            -- 医保分类名称（医保甲类/医保乙类）
    dosage_form TEXT,          -- 剂型
    category_name TEXT,        -- 药品分类路径
    drug_type_name TEXT       -- 药品类型（西药部分/中成药部分/中药饮片等）
)
```

## 药品类型

| drug_type_name | 说明 |
|---|---|
| 西药部分 / 西药 | 西药，可医保报销 |
| 中成药部分 / 中成药 | 中成药 |
| 竞价药品部分 | 协议期内谈判药品 |
| 基金予以支付的中药饮片 | 可报销的中药饮片（892种） |
| 不得纳入基金支付范围的中药饮片 | 自费中药饮片 |

## 医保分类

| kind_name | 说明 |
|---|---|
| 医保甲类 | 全额报销 |
| 医保乙类 | 按比例报销，需自付一部分 |
| None | 不在医保目录内 |

## Claude Code 技能

本项目内置两个医生技能：

### /doctor_yeah

只开西药，只推荐医保报销药品。适用于明确只要西药和医保报销的用户。

### /doctor_soyo

中西药都可以推荐，会询问患者偏好（是否要报销、是否能接受中药等），并给出报销/自费两种方案。

---

数据来源：[国家医保服务平台](https://wx.nhsa.gov.cn)
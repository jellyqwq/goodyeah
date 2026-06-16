# GoodYeah

国家医保药品/耗材目录查询工具，支持症状问诊和药品推荐。

## 项目结构

```
goodyeah/
├── drugs.db                       # SQLite 数据库，医保药品数据（4750 条）
├── 4750.json                     # 药品原始 API 响应数据
├── supplies_20260427.db           # SQLite 数据库，医用耗材数据（~11 万条）
├── main.py                       # 药品数据 CLI 入口（fetch/import/update）
├── fetch_std_drugs.py            # 耗材数据抓取脚本
├── fetch_std_details.py           # 耗材详情抓取脚本（根据 specificationCode 逐个抓取）
├── import_to_sqlite.py           # 药品 JSON 导入数据库
├── pyproject.toml                # Python 依赖配置
├── 药品目录凡例.md               # 《药品目录》凡例（政策说明）
├── .claude/
│   └── skills/
│       ├── doctor_yeah.md       # 医生好耶技能（西药、只开医保药）
│       └── doctor_soyo.md        # 医生 Soyo 技能（中西药皆可、询问患者偏好）
└── .venv/                        # uv 虚拟环境
```

## 快速开始

### 环境安装

```bash
uv sync
source .venv/bin/activate
```

## 药品数据

### CLI 入口

```bash
# 一键更新（获取 API 数据并导入数据库）
uv run python main.py update

# 仅从 API 获取数据
uv run python main.py fetch

# 仅将 JSON 导入数据库
uv run python main.py import
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
```

### 药品数据库表结构

```sql
CREATE TABLE drugs (
    id INTEGER PRIMARY KEY,
    name TEXT,                 -- 药品名称
    drug_type_id INTEGER,      -- 药品类型ID
    category_id INTEGER,      -- 分类ID
    kind INTEGER,              -- 医保类型（1=甲类，2=乙类）
    kind_name TEXT,            -- 医保分类名称
    dosage_form TEXT,          -- 剂型
    category_name TEXT,        -- 药品分类路径
    drug_type_name TEXT        -- 药品类型
)
```

## 耗材数据

### 抓取耗材列表

```bash
# 开始/继续抓取（自动从 checkpoint 恢复）
uv run python fetch_std_drugs.py run

# 测试
uv run python fetch_std_drugs.py test

# 重置从头开始
uv run python fetch_std_drugs.py reset
```

数据保存到 `supplies_20260427.db`，`releaseVersion` 作为文件名后缀。

### 抓取耗材详情

每个 `specificationCode` 对应多条详情记录（如规格型号等）：

```bash
# 开始/继续抓取（OCR 自动识别验证码）
uv run python fetch_std_details.py run

# 测试
uv run python fetch_std_details.py test

# 重置从头开始
uv run python fetch_std_details.py reset
```

**注意**：详情接口有反爬限制，被限流（405）时需等待几分钟后重试。

### 耗材数据库表结构

**supplies_xxxx.db**（耗材列表）：

```sql
CREATE TABLE drugs (
    specificationcode TEXT UNIQUE,  -- 规格编码（主键）
    commonname TEXT,                 -- 品名
    companyname TEXT,                -- 申报企业
    catalogname1 TEXT,               -- 一级分类
    catalogname2 TEXT,               -- 二级分类
    catalogname3 TEXT,               -- 三级分类
    genericname TEXT,               -- 通用名
    mediclevel TEXT,                 -- 收费等级
    isimported TEXT,                -- 是否进口
    isreimbursed TEXT,              -- 是否报销
    reimbursementratio TEXT,         -- 报销比例
    formularytype TEXT,             -- 处方类型
    hospitallevel TEXT,              -- 医院级别
    remark TEXT,                     -- 备注
    auditdate TEXT,                  -- 审核日期
    releaseversion TEXT,             -- 发布版本
    releaseversion2 TEXT             -- 发布版本2
)
```

**supply_details.db**（耗材详情）：

```sql
CREATE TABLE supply_details (
    id TEXT PRIMARY KEY,            -- 主键
    specificationcode TEXT,          -- 规格编码
    registrant TEXT,                 -- 注册人
    catalogname1 TEXT,               -- 一级分类
    catalogname2 TEXT,               -- 二级分类
    catalogname3 TEXT,               -- 三级分类
    commonname TEXT,                 -- 品名
    matrial TEXT,                   -- 材质
    characteristic TEXT,             -- 特征
    regcardnm TEXT,                 -- 注册证号
    regdSt TEXT,                    -- 注册证开始日期
    regdEd TEXT,                    -- 注册证结束日期
    oldRegcardNm TEXT,              -- 原注册证号
    regcardName TEXT,               -- 注册证名称
    productName TEXT,               -- 产品名称
    unit TEXT,                       -- 单位
    companyName TEXT,                -- 企业名称
    businessLicense TEXT,            -- 营业执照
    releaseVersion TEXT,             -- 发布版本
    ggxhCount TEXT,                 -- 规格型号数量
    specification TEXT,              -- 规格
    model TEXT,                     -- 型号
    udiCode TEXT,                  -- UDI 码
    codeCount TEXT,                 -- 代码数量
    dataResource TEXT,             -- 数据来源
    genericnumber TEXT,             -- 通用编号
    genericname TEXT                -- 通用名称
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

数据来源：[国家医保服务平台](https://wx.nhsa.gov.cn) / [国家医保局编码标准动态](https://code.nhsa.gov.cn)
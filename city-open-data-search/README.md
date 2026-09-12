# 城市开放资料搜索

索引城市**公开政策、地图、统计表与 PDF 附件元数据**，提供全文搜索与
**时间 / 类型 / 部门**过滤；详情页展示**摘要、文件清单与相似资料**。

- 🔍 全文搜索：SQLite FTS5 + 中文二元组分词，结果关键词高亮
- 🗂 四类资料：政策文件 / 地图 / 统计表 / PDF 附件（元数据）
- 🔎 三维过滤：发布时间区间、资料类型、发布部门（附分面计数）
- 📄 详情页：摘要、附件清单（格式/大小/MD5）、相似资料及推荐理由
- 🧰 零依赖：仅 Python 3.8+ 标准库，无需安装任何第三方包

## 目录结构

```
city-open-data-search/
├── run.py                     # 启动入口（库为空时自动导入示例数据）
├── app/
│   ├── tokenizer.py           # 中文二元组分词（索引与查询共用）
│   ├── db.py                  # SQLite + FTS5 表结构
│   ├── search.py              # 搜索 / 过滤 / 高亮 / 相似资料
│   ├── server.py              # HTTP 服务：页面路由 + JSON API
│   └── templates.py           # 搜索页与详情页模板
├── scripts/
│   ├── import_data.py         # 导入脚本（JSON / CSV）
│   └── make_sample_data.py    # 生成示例数据
├── data/
│   ├── sample/documents.json  # 示例数据（21 条资料、39 个附件）
│   └── opendata.db            # SQLite 数据库（导入后生成）
└── tests/test_search.py       # 30 个单元测试
```

## 本地部署

**环境要求**：Python ≥ 3.8（无需 pip，无需网络）。

```bash
cd city-open-data-search

# 1. 生成示例数据（首次）
python3 scripts/make_sample_data.py

# 2. 导入数据建立索引
python3 scripts/import_data.py data/sample/documents.json --reset

# 3. 启动服务
python3 run.py                      # http://127.0.0.1:8000
python3 run.py --host 0.0.0.0 --port 8080   # 自定义监听地址
```

打开浏览器访问 <http://127.0.0.1:8000> 即可搜索；点击结果进入详情页。

> 若跳过第 1、2 步直接 `python3 run.py`，检测到空库会自动导入示例数据。

运行测试：

```bash
python3 -m unittest discover -s tests -v
```

## 搜索接口（JSON API）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/search` | 全文搜索 + 过滤 + 分面 |
| GET | `/api/documents/<id>` | 资料详情（含文件清单、相似资料） |
| GET | `/api/documents/<id>/similar` | 相似资料列表 |
| GET | `/api/facets` | 部门 / 类型枚举 |
| GET | `/api/stats` | 索引统计 |

### `/api/search` 参数

| 参数 | 说明 | 示例 |
|---|---|---|
| `q` | 关键词（中文按二元组匹配） | `q=交通` |
| `type` | `policy` / `map` / `statistics` / `pdf_attachment` | `type=policy` |
| `department` | 发布部门全称 | `department=统计局` |
| `date_from` / `date_to` | 发布日期区间（ISO） | `date_from=2024-01-01` |
| `sort` | `relevance`（默认）/ `date` | `sort=date` |
| `page` / `size` | 分页（size ≤ 50） | `page=2&size=20` |

示例：

```bash
curl 'http://127.0.0.1:8000/api/search?q=空气&type=policy&date_from=2024-01-01'
curl 'http://127.0.0.1:8000/api/documents/POL-2026-003'
```

返回中包含 `results[].snippet`（`<mark>` 高亮片段）与
`facets`（当前条件下的部门/类型计数），可直接用于前端筛选栏。

## 数据导入

支持 **JSON** 与 **CSV** 两种格式，按 `id` 幂等更新（重复导入不产生重复数据）。

```bash
# JSON
python3 scripts/import_data.py data/sample/documents.json --reset

# CSV（附件清单独立成表）
python3 scripts/import_data.py documents.csv --files files.csv

# 常用选项
--db data/opendata.db   # 指定数据库路径
--reset                 # 导入前清空重建
--strict                # 遇到错误立即中止
```

JSON 记录格式：

```json
{
  "id": "POL-2024-001",
  "title": "……",
  "summary": "……",
  "content": "……（正文，参与全文索引）",
  "doc_type": "policy",
  "department": "交通运输局",
  "published_date": "2024-03-15",
  "tags": ["交通", "停车"],
  "source_url": "https://……",
  "files": [
    {"filename": "条例全文.pdf", "format": "pdf", "size_bytes": 102400,
     "url": "https://……", "checksum": "md5……"}
  ]
}
```

- `doc_type` 取值：`policy`（政策文件）、`map`（地图）、
  `statistics`（统计表）、`pdf_attachment`（PDF 附件）
- 日期兼容 `2024-3-5`、`2024/03/05`、`2024年3月5日`、`20240305`
- CSV 主表列：`id,title,summary,content,doc_type,department,published_date,tags(|分隔),source_url`；
  附件表列：`document_id,filename,format,size_bytes,url,checksum`

## 实现要点

- **中文检索**：FTS5 默认分词器不切分中文，本系统在索引与查询两侧统一做
  二元组（bigram）预切分（`app/tokenizer.py`），“交通”可命中“公共交通规划”。
- **相似资料**：共同标签（3 分/个）+ 同部门（2 分）+ 同类型（1 分）+
  标题词重叠（1 分/个）加权排序，并输出可解释的推荐理由。
- **事务导入**：单事务批量写入，附件与 FTS 索引随文档同步更新。

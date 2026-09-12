#!/usr/bin/env python3
"""资料导入脚本：把公开政策、地图、统计表与 PDF 附件元数据导入搜索索引。

用法：
    python3 scripts/import_data.py data/sample/documents.json
    python3 scripts/import_data.py documents.csv --files files.csv
    python3 scripts/import_data.py data.json --db data/opendata.db --reset

JSON 格式（列表，每个元素一条资料）：
[
  {
    "id": "POL-2024-001",                 # 必填，唯一编号
    "title": "……",                        # 必填
    "summary": "……",                      # 摘要
    "content": "……",                      # 正文/说明（参与全文索引）
    "doc_type": "policy",                 # policy|map|statistics|pdf_attachment
    "department": "交通运输局",            # 必填
    "published_date": "2024-03-15",       # 支持 2024-3-5 / 2024/3/5 / 2024年3月5日 / 20240305
    "tags": ["交通", "停车"],
    "source_url": "https://……",
    "files": [                            # 附件清单（PDF 附件元数据等）
      {"filename": "……", "format": "pdf", "size_bytes": 102400,
       "url": "https://……", "checksum": "md5……"}
    ]
  }
]

CSV 格式：主表列 id,title,summary,content,doc_type,department,published_date,
tags(用 | 分隔),source_url；附件表（--files）列
document_id,filename,format,size_bytes,url,checksum。
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db as dbmod          # noqa: E402
from app.tokenizer import tokenize   # noqa: E402

REQUIRED = ("id", "title", "doc_type", "department", "published_date")


class ImportError_(Exception):
    pass


# ------------------------------------------------------------------ 校验

def normalize_date(value):
    """把多种日期写法归一化为 ISO YYYY-MM-DD。"""
    s = str(value).strip()
    m = re.fullmatch(r"(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})日?", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    elif re.fullmatch(r"\d{8}", s):
        y, mo, d = int(s[:4]), int(s[4:6]), int(s[6:8])
    else:
        raise ImportError_(f"无法识别的日期格式: {value!r}")
    try:
        return dt.date(y, mo, d).isoformat()
    except ValueError as exc:
        raise ImportError_(f"非法日期 {value!r}: {exc}") from exc


def validate_doc(raw, lineno="?"):
    """校验并归一化一条资料记录，返回干净字典。"""
    if not isinstance(raw, dict):
        raise ImportError_(f"第 {lineno} 条：记录必须是对象")
    doc = {k: (raw.get(k) or "") for k in
           ("id", "title", "summary", "content", "doc_type",
            "department", "source_url")}
    for k in REQUIRED:
        if not str(raw.get(k) or "").strip():
            raise ImportError_(f"第 {lineno} 条：缺少必填字段 {k!r}")
    doc["id"] = str(doc["id"]).strip()
    doc["title"] = str(doc["title"]).strip()
    doc["department"] = str(doc["department"]).strip()
    doc["doc_type"] = str(doc["doc_type"]).strip()
    if doc["doc_type"] not in dbmod.DOC_TYPES:
        raise ImportError_(
            f"第 {lineno} 条：doc_type 必须是 {sorted(dbmod.DOC_TYPES)} 之一，"
            f"得到 {doc['doc_type']!r}")
    doc["published_date"] = normalize_date(raw["published_date"])

    tags = raw.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in re.split(r"[|;,，；]", tags) if t.strip()]
    if not isinstance(tags, list):
        raise ImportError_(f"第 {lineno} 条：tags 必须是数组或分隔字符串")
    doc["tags"] = [str(t).strip() for t in tags if str(t).strip()]

    files = raw.get("files") or []
    if not isinstance(files, list):
        raise ImportError_(f"第 {lineno} 条：files 必须是数组")
    doc["files"] = []
    for i, f in enumerate(files):
        if not isinstance(f, dict) or not str(f.get("filename") or "").strip():
            raise ImportError_(f"第 {lineno} 条：files[{i}] 缺少 filename")
        try:
            size = int(f.get("size_bytes") or 0)
        except (TypeError, ValueError):
            raise ImportError_(f"第 {lineno} 条：files[{i}].size_bytes 非数字")
        doc["files"].append({
            "filename": str(f["filename"]).strip(),
            "format": str(f.get("format") or "").strip().lower().lstrip("."),
            "size_bytes": max(0, size),
            "url": str(f.get("url") or "").strip(),
            "checksum": str(f.get("checksum") or "").strip(),
        })
    return doc


# ------------------------------------------------------------------ 写入

def upsert_document(conn, doc):
    """插入或更新一条资料及其附件与全文索引。"""
    conn.execute(
        """INSERT INTO documents
             (id, title, summary, content, doc_type, department,
              published_date, tags, source_url)
           VALUES (?,?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
             title=excluded.title, summary=excluded.summary,
             content=excluded.content, doc_type=excluded.doc_type,
             department=excluded.department,
             published_date=excluded.published_date,
             tags=excluded.tags, source_url=excluded.source_url""",
        (doc["id"], doc["title"], doc["summary"], doc["content"],
         doc["doc_type"], doc["department"], doc["published_date"],
         json.dumps(doc["tags"], ensure_ascii=False), doc["source_url"]))

    conn.execute("DELETE FROM files WHERE document_id = ?", (doc["id"],))
    conn.executemany(
        "INSERT INTO files (document_id, filename, format, size_bytes, url,"
        " checksum) VALUES (?,?,?,?,?,?)",
        [(doc["id"], f["filename"], f["format"], f["size_bytes"],
          f["url"], f["checksum"]) for f in doc["files"]])

    rowid = conn.execute(
        "SELECT rowid FROM documents WHERE id = ?", (doc["id"],)).fetchone()[0]
    conn.execute("DELETE FROM docs_fts WHERE rowid = ?", (rowid,))
    full_text = " ".join([doc["title"], doc["title"],  # 标题加权
                          doc["summary"], doc["content"],
                          " ".join(doc["tags"]), doc["department"]])
    conn.execute("INSERT INTO docs_fts (rowid, text) VALUES (?, ?)",
                 (rowid, tokenize(full_text)))


# ------------------------------------------------------------------ 读取

def load_json(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ImportError_("JSON 顶层必须是数组")
    return data


def load_csv(path, files_path=None):
    docs = {}
    order = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            row = {k: (v or "") for k, v in row.items()}
            row["files"] = []
            docs[row.get("id", "")] = row
            order.append(row.get("id", ""))
    if files_path:
        with open(files_path, newline="", encoding="utf-8-sig") as fh:
            for f in csv.DictReader(fh):
                doc = docs.get((f.get("document_id") or "").strip())
                if doc is None:
                    print(f"  ⚠ 附件 {f.get('filename')!r} 指向未知资料 "
                          f"{f.get('document_id')!r}，已跳过", file=sys.stderr)
                    continue
                doc["files"].append({
                    "filename": f.get("filename", ""),
                    "format": f.get("format", ""),
                    "size_bytes": f.get("size_bytes", "0"),
                    "url": f.get("url", ""),
                    "checksum": f.get("checksum", ""),
                })
    return [docs[i] for i in order]


# ------------------------------------------------------------------ 入口

def import_file(path, db_path, files_path=None, reset=False, strict=False):
    if reset and os.path.exists(db_path):
        os.remove(db_path)
    conn = dbmod.init_db(db_path)

    if path.lower().endswith(".json"):
        raw_docs = load_json(path)
    else:
        raw_docs = load_csv(path, files_path)

    ok, failed = 0, 0
    with conn:
        for i, raw in enumerate(raw_docs, 1):
            try:
                doc = validate_doc(raw, i)
                upsert_document(conn, doc)
                ok += 1
            except ImportError_ as exc:
                failed += 1
                print(f"  ✗ {exc}", file=sys.stderr)
                if strict:
                    raise
    total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    conn.close()
    print(f"✔ 导入完成：成功 {ok} 条，失败 {failed} 条；库内共 {total} 条"
          f"（{db_path}）")
    return ok, failed


def main(argv=None):
    ap = argparse.ArgumentParser(description="城市开放资料导入脚本")
    ap.add_argument("input", help="资料文件（.json 或 .csv）")
    ap.add_argument("--files", help="附件清单 CSV（配合 CSV 主表使用）")
    ap.add_argument("--db", default="data/opendata.db", help="SQLite 数据库路径")
    ap.add_argument("--reset", action="store_true", help="导入前清空数据库")
    ap.add_argument("--strict", action="store_true", help="遇到错误立即中止")
    args = ap.parse_args(argv)
    _, failed = import_file(args.input, args.db, args.files,
                            reset=args.reset, strict=args.strict)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

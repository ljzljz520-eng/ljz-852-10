"""数据库层：SQLite + FTS5 全文索引。"""
import os
import sqlite3

# 资料类型 -> 中文标签
DOC_TYPES = {
    "policy": "政策文件",
    "map": "地图",
    "statistics": "统计表",
    "pdf_attachment": "PDF 附件",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id             TEXT PRIMARY KEY,          -- 资料编号，如 POL-2024-001
    title          TEXT NOT NULL,
    summary        TEXT NOT NULL DEFAULT '',  -- 摘要
    content        TEXT NOT NULL DEFAULT '',  -- 正文/说明（参与全文索引）
    doc_type       TEXT NOT NULL CHECK (doc_type IN
                     ('policy','map','statistics','pdf_attachment')),
    department     TEXT NOT NULL,             -- 发布部门
    published_date TEXT NOT NULL,             -- ISO 日期 YYYY-MM-DD
    tags           TEXT NOT NULL DEFAULT '[]',-- JSON 数组
    source_url     TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS files (            -- 附件清单（含 PDF 附件元数据）
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    filename    TEXT NOT NULL,
    format      TEXT NOT NULL DEFAULT '',     -- pdf / csv / xlsx / shp ...
    size_bytes  INTEGER NOT NULL DEFAULT 0,
    url         TEXT NOT NULL DEFAULT '',
    checksum    TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_files_doc  ON files(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_type   ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_doc_dept   ON documents(department);
CREATE INDEX IF NOT EXISTS idx_doc_date   ON documents(published_date);

-- 全文索引：text 列为 tokenizer.tokenize() 预切分后的文本
CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
    text,
    tokenize='unicode61'
);
"""


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path):
    """创建（如不存在）数据库与表结构，返回连接。"""
    parent = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(parent, exist_ok=True)
    conn = connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn

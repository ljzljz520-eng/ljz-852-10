"""搜索与检索逻辑：全文搜索、条件过滤、摘要高亮、相似资料推荐。"""
import html
import json

from .db import DOC_TYPES
from .tokenizer import tokenize, query_terms

PAGE_SIZE_MAX = 50


# ---------------------------------------------------------------- 工具

def row_to_doc(row):
    d = dict(row)
    d.pop("rank", None)
    try:
        d["tags"] = json.loads(d.get("tags") or "[]")
    except (ValueError, TypeError):
        d["tags"] = []
    d["type_label"] = DOC_TYPES.get(d["doc_type"], d["doc_type"])
    return d


def highlight(text, terms):
    """在 text 中用 <mark> 标出所有 terms（自动合并重叠区间，输出已转义）。"""
    if not text:
        return ""
    spans = []
    low = text.lower()
    for t in terms:
        if not t:
            continue
        start = 0
        while True:
            i = low.find(t, start)
            if i < 0:
                break
            spans.append((i, i + len(t)))
            start = i + 1
    if not spans:
        return html.escape(text)
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    out, pos = [], 0
    for s, e in merged:
        out.append(html.escape(text[pos:s]))
        out.append("<mark>" + html.escape(text[s:e]) + "</mark>")
        pos = e
    out.append(html.escape(text[pos:]))
    return "".join(out)


def make_snippet(doc, query, width=160):
    """从摘要/正文中截取包含查询词的片段并高亮；无命中时取摘要开头。"""
    terms = query_terms(query)
    summary, content = doc.get("summary", ""), doc.get("content", "")
    if not terms:
        text = summary or content
        return html.escape(text[:width]) + ("…" if len(text) > width else "")
    # 优先在摘要中找命中点，其次正文
    for text in (summary, content, doc.get("title", "")):
        low = text.lower()
        hit = min((low.find(t) for t in terms if low.find(t) >= 0), default=-1)
        if hit >= 0:
            start = max(0, hit - width // 3)
            frag = text[start:start + width]
            prefix = "…" if start > 0 else ""
            suffix = "…" if start + width < len(text) else ""
            return prefix + highlight(frag, terms) + suffix
    text = summary or content
    return html.escape(text[:width]) + ("…" if len(text) > width else "")


# ---------------------------------------------------------------- 搜索

def _clamp(value, lo, hi, default):
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def search(conn, q="", doc_type=None, department=None,
           date_from=None, date_to=None, page=1, size=10, sort="relevance"):
    """全文搜索 + 过滤。返回 total / results / facets / 分页信息。"""
    page = _clamp(page, 1, 10 ** 9, 1)
    size = _clamp(size, 1, PAGE_SIZE_MAX, 10)
    fts_query = tokenize(q)

    where, params = [], []
    if fts_query:
        where.append("docs_fts MATCH ?")
        params.append(fts_query)
    if doc_type:
        where.append("d.doc_type = ?")
        params.append(doc_type)
    if department:
        where.append("d.department = ?")
        params.append(department)
    if date_from:
        where.append("d.published_date >= ?")
        params.append(date_from)
    if date_to:
        where.append("d.published_date <= ?")
        params.append(date_to)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    if fts_query:
        from_sql = "FROM docs_fts JOIN documents d ON d.rowid = docs_fts.rowid"
        order_sql = ("ORDER BY d.published_date DESC, d.id" if sort == "date"
                     else "ORDER BY bm25(docs_fts), d.published_date DESC")
        select_extra = ", bm25(docs_fts) AS rank"
    else:
        from_sql = "FROM documents d"
        order_sql = "ORDER BY d.published_date DESC, d.id"
        select_extra = ""

    total = conn.execute(
        f"SELECT COUNT(*) {from_sql} {where_sql}", params).fetchone()[0]

    rows = conn.execute(
        f"SELECT d.*{select_extra} {from_sql} {where_sql} {order_sql} "
        f"LIMIT ? OFFSET ?", params + [size, (page - 1) * size]).fetchall()

    results = []
    for r in rows:
        doc = row_to_doc(r)
        doc["snippet"] = make_snippet(doc, q)
        results.append(doc)

    facets = {
        "departments": [dict(r) for r in conn.execute(
            f"SELECT d.department AS name, COUNT(*) AS count {from_sql} "
            f"{where_sql} GROUP BY d.department ORDER BY count DESC, name",
            params)],
        "types": [dict(r) for r in conn.execute(
            f"SELECT d.doc_type AS name, COUNT(*) AS count {from_sql} "
            f"{where_sql} GROUP BY d.doc_type ORDER BY count DESC", params)],
    }
    for t in facets["types"]:
        t["label"] = DOC_TYPES.get(t["name"], t["name"])

    return {
        "query": {"q": q, "type": doc_type or "", "department": department or "",
                  "date_from": date_from or "", "date_to": date_to or "",
                  "sort": sort},
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, -(-total // size)),
        "results": results,
        "facets": facets,
    }


# ---------------------------------------------------------------- 详情

def get_document(conn, doc_id):
    row = conn.execute(
        "SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if row is None:
        return None
    doc = row_to_doc(row)
    doc["files"] = [dict(r) for r in conn.execute(
        "SELECT id, filename, format, size_bytes, url, checksum "
        "FROM files WHERE document_id = ? ORDER BY id", (doc_id,))]
    return doc


def similar_documents(conn, doc_id, limit=6):
    """相似资料推荐：共同标签(3分/个) + 同部门(2) + 同类型(1) + 标题词重叠(1/个)。"""
    doc = get_document(conn, doc_id)
    if doc is None:
        return []
    base_tags = set(doc["tags"])
    base_terms = set(tokenize(doc["title"]).split())

    scored = []
    rows = conn.execute(
        "SELECT * FROM documents WHERE id != ?", (doc_id,)).fetchall()
    for r in rows:
        other = row_to_doc(r)
        shared = base_tags & set(other["tags"])
        score = 3 * len(shared)
        reasons = []
        if shared:
            reasons.append("共同标签：" + "、".join(sorted(shared)))
        if other["department"] == doc["department"]:
            score += 2
            reasons.append("同一部门")
        if other["doc_type"] == doc["doc_type"]:
            score += 1
            reasons.append("同一类型")
        overlap = base_terms & set(tokenize(other["title"]).split())
        score += len(overlap)
        if overlap:
            reasons.append("标题关键词相近")
        if score <= 0:
            continue
        scored.append({
            "score": score,
            "reasons": reasons,
            "id": other["id"],
            "title": other["title"],
            "doc_type": other["doc_type"],
            "type_label": other["type_label"],
            "department": other["department"],
            "published_date": other["published_date"],
            "summary": other["summary"],
        })
    scored.sort(key=lambda x: (x["score"], x["published_date"]), reverse=True)
    return scored[:limit]


# ---------------------------------------------------------------- 统计

def stats(conn):
    by_type = [dict(r) for r in conn.execute(
        "SELECT doc_type AS name, COUNT(*) AS count FROM documents "
        "GROUP BY doc_type ORDER BY count DESC")]
    for t in by_type:
        t["label"] = DOC_TYPES.get(t["name"], t["name"])
    by_dept = [dict(r) for r in conn.execute(
        "SELECT department AS name, COUNT(*) AS count FROM documents "
        "GROUP BY department ORDER BY count DESC, name")]
    files = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(size_bytes),0) AS bytes FROM files"
    ).fetchone()
    rng = conn.execute(
        "SELECT MIN(published_date) AS lo, MAX(published_date) AS hi "
        "FROM documents").fetchone()
    return {
        "documents": sum(t["count"] for t in by_type),
        "files": files["n"],
        "file_bytes": files["bytes"],
        "date_range": [rng["lo"], rng["hi"]],
        "by_type": by_type,
        "by_department": by_dept,
    }

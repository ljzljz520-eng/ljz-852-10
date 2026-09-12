"""中文友好的分词器。

SQLite FTS5 自带的 unicode61 分词器不会切分中文（整段中文会被视为一个词），
导致“交通”无法命中“公共交通规划”。本模块在【写入索引】和【执行查询】时
使用同一套规则做预切分：

- 连续 CJK 汉字 -> 重叠二元组（bigram），单字保留单字；
  例：“公共交通” -> “公共 共交 交通”
- 连续字母/数字 -> 整体作为一个词（统一小写）。
  例：“GDP2024” -> “gdp2024”
"""
import re

_TOKEN_RE = re.compile(r"[一-鿿㐀-䶿豈-﫿]+|[a-zA-Z0-9]+")
_CJK_RE = re.compile(r"^[一-鿿㐀-䶿豈-﫿]+$")


def tokenize(text):
    """把任意文本切分为空格分隔的词序列，供 FTS5 索引/查询使用。"""
    if not text:
        return ""
    tokens = []
    for m in _TOKEN_RE.finditer(text.lower()):
        seg = m.group(0)
        if _CJK_RE.match(seg):
            if len(seg) == 1:
                tokens.append(seg)
            else:
                tokens.extend(seg[i:i + 2] for i in range(len(seg) - 1))
        else:
            tokens.append(seg)
    return " ".join(tokens)


def query_terms(query):
    """从原始查询中提取用于高亮的词：完整中文片段 + 二元组 + 英文词。"""
    if not query:
        return []
    terms = []
    for m in _TOKEN_RE.finditer(query.lower()):
        seg = m.group(0)
        terms.append(seg)
        if _CJK_RE.match(seg) and len(seg) > 2:
            terms.extend(seg[i:i + 2] for i in range(len(seg) - 1))
    # 去重，长词优先（高亮时先匹配长词）
    seen, out = set(), []
    for t in sorted(terms, key=len, reverse=True):
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out

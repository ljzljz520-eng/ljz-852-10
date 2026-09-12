"""页面模板：搜索首页（前端调用 JSON API）与资料详情页（服务端渲染）。"""
import html


def esc(s):
    return html.escape(str(s or ""), quote=True)


def human_size(n):
    n = int(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n} B"


def layout(title, body):
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · 城市开放资料搜索</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="/">🏙️ 城市开放资料搜索</a>
    <span class="tagline">公开政策 · 地图 · 统计表 · PDF 附件元数据</span>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="site-footer wrap">城市开放资料搜索 · 本地演示实例 · 数据为示例数据</footer>
</body>
</html>"""


INDEX_BODY = """
<div class="search-panel">
  <form id="search-form" class="search-bar">
    <input id="q" type="search" placeholder="输入关键词，如：交通、学区、空气质量、人口…" autofocus>
    <button type="submit">搜索</button>
  </form>
  <div class="filters">
    <label>类型 <select id="type">
      <option value="">全部</option>
      <option value="policy">政策文件</option>
      <option value="map">地图</option>
      <option value="statistics">统计表</option>
      <option value="pdf_attachment">PDF 附件</option>
    </select></label>
    <label>部门 <select id="department"><option value="">全部</option></select></label>
    <label>时间 <input type="date" id="date_from"> 至 <input type="date" id="date_to"></label>
    <label>排序 <select id="sort">
      <option value="relevance">相关度</option>
      <option value="date">发布时间</option>
    </select></label>
  </div>
</div>
<div class="content">
  <aside id="facets"></aside>
  <section class="results-col">
    <div id="meta" class="meta"></div>
    <div id="results"></div>
    <div id="pager" class="pager"></div>
  </section>
</div>
<script>
const $ = id => document.getElementById(id);
const TYPE_LABELS = {policy:'政策文件', map:'地图', statistics:'统计表', pdf_attachment:'PDF 附件'};
let state = {page: 1};

function params(page) {
  const p = new URLSearchParams();
  for (const k of ['q','type','department','date_from','date_to','sort']) {
    const v = $(k).value.trim();
    if (v) p.set(k, v);
  }
  p.set('page', page || 1);
  return p;
}

async function doSearch(page) {
  const p = params(page);
  history.replaceState(null, '', '/?' + p.toString());
  const res = await fetch('/api/search?' + p.toString());
  const data = await res.json();
  renderMeta(data); renderResults(data); renderFacets(data); renderPager(data);
  state.page = data.page;
}

function renderMeta(d) {
  $('meta').textContent = d.total
    ? `共 ${d.total} 条结果，第 ${d.page}/${d.pages} 页`
    : '未找到匹配的资料，请调整关键词或过滤条件';
}

function renderResults(d) {
  $('results').innerHTML = d.results.map(r => `
    <article class="card">
      <div class="card-head">
        <span class="badge t-${r.doc_type}">${r.type_label}</span>
        <a class="title" href="/document/${encodeURIComponent(r.id)}">${escapeHtml(r.title)}</a>
      </div>
      <p class="snippet">${r.snippet}</p>
      <p class="meta-line">🏛 ${escapeHtml(r.department)} · 📅 ${r.published_date}
        ${r.tags.map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}</p>
    </article>`).join('');
}

function renderFacets(d) {
  const dep = d.facets.departments.map(f =>
    `<li><a href="#" data-k="department" data-v="${escapeHtml(f.name)}">${escapeHtml(f.name)}</a> <em>${f.count}</em></li>`).join('');
  const typ = d.facets.types.map(f =>
    `<li><a href="#" data-k="type" data-v="${f.name}">${f.label}</a> <em>${f.count}</em></li>`).join('');
  $('facets').innerHTML = `<h3>按部门筛选</h3><ul>${dep || '<li class="none">无</li>'}</ul>
                           <h3>按类型筛选</h3><ul>${typ || '<li class="none">无</li>'}</ul>`;
  $('facets').querySelectorAll('a').forEach(a => a.onclick = e => {
    e.preventDefault();
    $(a.dataset.k).value = a.dataset.v;
    doSearch(1);
  });
}

function renderPager(d) {
  if (d.pages <= 1) { $('pager').innerHTML = ''; return; }
  let btns = [];
  for (let i = 1; i <= d.pages; i++) {
    btns.push(i === d.page ? `<b>${i}</b>` : `<a href="#" data-p="${i}">${i}</a>`);
  }
  $('pager').innerHTML = btns.join(' ');
  $('pager').querySelectorAll('a').forEach(a => a.onclick = e => {
    e.preventDefault(); doSearch(+a.dataset.p);
  });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

$('search-form').onsubmit = e => { e.preventDefault(); doSearch(1); };
for (const k of ['type','department','sort']) $(k).onchange = () => doSearch(1);
for (const k of ['date_from','date_to']) $(k).onchange = () => doSearch(1);

(async function init() {
  // 从 URL 恢复查询条件
  const u = new URLSearchParams(location.search);
  for (const k of ['q','type','department','date_from','date_to','sort'])
    if (u.get(k)) $(k).value = u.get(k);
  // 填充部门下拉
  const f = await (await fetch('/api/facets')).json();
  $('department').innerHTML = '<option value="">全部</option>' +
    f.departments.map(d => `<option ${d.name === $('department').value ? 'selected' : ''}>${escapeHtml(d.name)}</option>`).join('');
  doSearch(+(u.get('page') || 1));
})();
</script>
"""


def detail_body(doc, similar):
    tags = " ".join(f'<span class="tag">{esc(t)}</span>' for t in doc["tags"])
    if doc["files"]:
        rows = "".join(
            f"<tr><td>{esc(f['filename'])}</td>"
            f"<td>{esc(f['format']).upper() or '—'}</td>"
            f"<td>{human_size(f['size_bytes'])}</td>"
            f"<td class='mono'>{esc(f['checksum']) or '—'}</td>"
            f"<td>{('<a href=' + chr(34) + esc(f['url']) + chr(34) + '>下载</a>') if f['url'] else '—'}</td></tr>"
            for f in doc["files"])
        files_html = f"""<table class="files">
<thead><tr><th>文件名</th><th>格式</th><th>大小</th><th>校验和 (MD5)</th><th>操作</th></tr></thead>
<tbody>{rows}</tbody></table>"""
    else:
        files_html = '<p class="none">该资料暂无附件。</p>'

    if similar:
        items = "".join(f"""
      <li class="sim-item">
        <span class="badge t-{s['doc_type']}">{esc(s['type_label'])}</span>
        <a href="/document/{esc(s['id'])}">{esc(s['title'])}</a>
        <span class="sim-meta">{esc(s['department'])} · {esc(s['published_date'])}</span>
        <span class="sim-why">{esc('；'.join(s['reasons']))}</span>
      </li>""" for s in similar)
        similar_html = f"<ul class='sim-list'>{items}</ul>"
    else:
        similar_html = '<p class="none">暂无相似资料。</p>'

    source = (f'<a href="{esc(doc["source_url"])}">原始出处 ↗</a>'
              if doc["source_url"] else "—")
    return f"""
<nav class="crumb"><a href="/">← 返回搜索</a></nav>
<article class="detail">
  <div class="card-head">
    <span class="badge t-{esc(doc['doc_type'])}">{esc(doc['type_label'])}</span>
    <h1>{esc(doc['title'])}</h1>
  </div>
  <dl class="meta-grid">
    <div><dt>资料编号</dt><dd class="mono">{esc(doc['id'])}</dd></div>
    <div><dt>发布部门</dt><dd>{esc(doc['department'])}</dd></div>
    <div><dt>发布日期</dt><dd>{esc(doc['published_date'])}</dd></div>
    <div><dt>来源</dt><dd>{source}</dd></div>
    <div><dt>标签</dt><dd>{tags or '—'}</dd></div>
  </dl>
  <h2>摘要</h2>
  <p class="summary">{esc(doc['summary'])}</p>
  {('<h2>正文说明</h2><p class="summary">' + esc(doc['content']) + '</p>') if doc['content'] else ''}
  <h2>文件清单（{len(doc['files'])}）</h2>
  {files_html}
  <h2>相似资料</h2>
  {similar_html}
</article>
"""


STYLE_CSS = """
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
       background: #f4f6f8; color: #222; }
.wrap { max-width: 1080px; margin: 0 auto; padding: 0 16px; }
.site-header { background: #1f4e79; color: #fff; padding: 14px 0; }
.site-header .wrap { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; }
.brand { color: #fff; font-size: 20px; font-weight: 700; text-decoration: none; }
.tagline { color: #bcd3ea; font-size: 13px; }
.site-footer { color: #999; font-size: 12px; padding: 24px 16px; }
.search-panel { background: #fff; border-radius: 10px; padding: 16px; margin: 20px 0;
                box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.search-bar { display: flex; gap: 8px; }
.search-bar input { flex: 1; padding: 10px 14px; font-size: 16px; border: 1px solid #ccd4dc; border-radius: 6px; }
.search-bar button { padding: 10px 26px; font-size: 16px; background: #1f4e79; color: #fff;
                     border: 0; border-radius: 6px; cursor: pointer; }
.search-bar button:hover { background: #2a629a; }
.filters { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 12px; font-size: 14px; color: #555; }
.filters select, .filters input { padding: 4px 6px; border: 1px solid #ccd4dc; border-radius: 4px; }
.content { display: flex; gap: 20px; align-items: flex-start; }
aside { width: 220px; flex-shrink: 0; background: #fff; border-radius: 10px; padding: 14px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,.08); font-size: 14px; }
aside h3 { margin: 10px 0 6px; font-size: 14px; color: #1f4e79; }
aside ul { list-style: none; margin: 0 0 8px; padding: 0; }
aside li { display: flex; justify-content: space-between; padding: 3px 0; }
aside a { color: #2a629a; text-decoration: none; }
aside a:hover { text-decoration: underline; }
aside em { color: #999; font-style: normal; }
aside .none { color: #bbb; }
.results-col { flex: 1; min-width: 0; }
.meta { color: #777; font-size: 13px; margin-bottom: 10px; }
.card { background: #fff; border-radius: 10px; padding: 14px 18px; margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.card-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.card-head h1 { font-size: 22px; margin: 6px 0; }
.title { font-size: 17px; font-weight: 600; color: #1f4e79; text-decoration: none; }
.title:hover { text-decoration: underline; }
.badge { font-size: 12px; padding: 2px 8px; border-radius: 10px; color: #fff; white-space: nowrap; }
.t-policy { background: #c0392b; } .t-map { background: #27ae60; }
.t-statistics { background: #8e44ad; } .t-pdf_attachment { background: #e67e22; }
.snippet { margin: 8px 0; line-height: 1.7; color: #444; font-size: 14px; }
mark { background: #ffe9a8; padding: 0 1px; border-radius: 2px; }
.meta-line { margin: 4px 0 0; font-size: 13px; color: #888; }
.tag { display: inline-block; background: #eef3f8; color: #1f4e79; border-radius: 4px;
       padding: 1px 7px; margin-left: 6px; font-size: 12px; }
.pager { text-align: center; margin: 18px 0 30px; }
.pager a, .pager b { display: inline-block; min-width: 30px; padding: 5px 0; margin: 0 3px;
                     border-radius: 5px; background: #fff; color: #1f4e79; text-decoration: none;
                     box-shadow: 0 1px 2px rgba(0,0,0,.1); }
.pager b { background: #1f4e79; color: #fff; }
.crumb { margin: 18px 0 10px; } .crumb a { color: #2a629a; text-decoration: none; }
.detail { background: #fff; border-radius: 10px; padding: 22px 26px; margin-bottom: 30px;
          box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.meta-grid { display: flex; flex-wrap: wrap; gap: 8px 28px; margin: 12px 0 4px; }
.meta-grid div { display: flex; gap: 8px; } 
.meta-grid dt { color: #999; } .meta-grid dd { margin: 0; }
.mono { font-family: ui-monospace, Consolas, monospace; font-size: 13px; }
.detail h2 { font-size: 16px; color: #1f4e79; border-left: 4px solid #1f4e79; padding-left: 8px; margin-top: 24px; }
.summary { line-height: 1.9; color: #333; }
table.files { width: 100%; border-collapse: collapse; font-size: 14px; }
table.files th, table.files td { border: 1px solid #e3e8ee; padding: 8px 10px; text-align: left; }
table.files th { background: #f0f4f8; }
.sim-list { list-style: none; padding: 0; margin: 0; }
.sim-item { padding: 10px 0; border-bottom: 1px dashed #e3e8ee; display: flex; gap: 8px;
            align-items: baseline; flex-wrap: wrap; }
.sim-item a { color: #1f4e79; font-weight: 600; text-decoration: none; }
.sim-item a:hover { text-decoration: underline; }
.sim-meta { color: #999; font-size: 12px; }
.sim-why { color: #b7850b; font-size: 12px; }
.none { color: #aaa; }
@media (max-width: 800px) { .content { flex-direction: column; } aside { width: 100%; } }
"""

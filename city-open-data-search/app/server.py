"""HTTP 服务：页面路由 + JSON 搜索 API（仅依赖标准库 wsgiref）。

API 一览
  GET /api/search?q=&type=&department=&date_from=&date_to=&sort=&page=&size=
  GET /api/documents/<id>          详情（含文件清单与相似资料）
  GET /api/documents/<id>/similar  相似资料
  GET /api/facets                  部门/类型分面计数
  GET /api/stats                   索引统计
"""
import json
import re
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

from . import db as dbmod
from . import search as searchmod
from . import templates


class _QuietHandler(WSGIRequestHandler):
    def log_message(self, fmt, *args):  # 精简日志
        print(f"  {self.address_string()} - {fmt % args}")


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class OpenDataApp:
    def __init__(self, db_path):
        self.db_path = db_path

    # ------------------------------------------------------------ 路由
    def __call__(self, environ, start_response):
        try:
            path = environ.get("PATH_INFO", "/")
            params = {k: v[0] for k, v in
                      parse_qs(environ.get("QUERY_STRING", "")).items()}
            status, ctype, body = self.route(path, params)
        except Exception as exc:  # noqa: BLE001
            status, ctype = "500 Internal Server Error", "application/json"
            body = json.dumps({"error": f"{type(exc).__name__}: {exc}"},
                              ensure_ascii=False)
        headers = [("Content-Type", f"{ctype}; charset=utf-8")]
        start_response(status, headers)
        return [body.encode("utf-8")]

    def route(self, path, params):
        if path == "/":
            return self.html(templates.layout("搜索", templates.INDEX_BODY))
        if path == "/static/style.css":
            return "200 OK", "text/css", templates.STYLE_CSS
        if path == "/api/search":
            return self.api_search(params)
        if path == "/api/facets":
            return self.api_facets()
        if path == "/api/stats":
            return self.api_stats()
        m = re.fullmatch(r"/api/documents/([^/]+)", path)
        if m:
            return self.api_document(m.group(1))
        m = re.fullmatch(r"/api/documents/([^/]+)/similar", path)
        if m:
            return self.api_similar(m.group(1))
        m = re.fullmatch(r"/document/([^/]+)", path)
        if m:
            return self.detail_page(m.group(1))
        return self.json_response({"error": "not found"}, "404 Not Found")

    # ------------------------------------------------------------ 响应
    @staticmethod
    def html(body, status="200 OK"):
        return status, "text/html", body

    @staticmethod
    def json_response(obj, status="200 OK"):
        return status, "application/json", json.dumps(obj, ensure_ascii=False)

    # ------------------------------------------------------------ 页面
    def detail_page(self, doc_id):
        with dbmod.connect(self.db_path) as conn:
            doc = searchmod.get_document(conn, doc_id)
            if doc is None:
                return self.html(
                    templates.layout("未找到", "<p class='none'>资料不存在或已下架。"
                                     " <a href='/'>返回搜索</a></p>"),
                    "404 Not Found")
            similar = searchmod.similar_documents(conn, doc_id)
        return self.html(templates.layout(
            doc["title"], templates.detail_body(doc, similar)))

    # ------------------------------------------------------------ API
    def api_search(self, p):
        with dbmod.connect(self.db_path) as conn:
            result = searchmod.search(
                conn,
                q=p.get("q", ""),
                doc_type=p.get("type") or None,
                department=p.get("department") or None,
                date_from=p.get("date_from") or None,
                date_to=p.get("date_to") or None,
                page=p.get("page", 1),
                size=p.get("size", 10),
                sort=p.get("sort", "relevance"),
            )
        return self.json_response(result)

    def api_document(self, doc_id):
        with dbmod.connect(self.db_path) as conn:
            doc = searchmod.get_document(conn, doc_id)
            if doc is None:
                return self.json_response({"error": "document not found"},
                                          "404 Not Found")
            doc["similar"] = searchmod.similar_documents(conn, doc_id)
        return self.json_response(doc)

    def api_similar(self, doc_id):
        with dbmod.connect(self.db_path) as conn:
            if searchmod.get_document(conn, doc_id) is None:
                return self.json_response({"error": "document not found"},
                                          "404 Not Found")
            similar = searchmod.similar_documents(conn, doc_id)
        return self.json_response({"id": doc_id, "similar": similar})

    def api_facets(self):
        with dbmod.connect(self.db_path) as conn:
            deps = [r[0] for r in conn.execute(
                "SELECT DISTINCT department FROM documents ORDER BY department")]
            types = [{"name": k, "label": v}
                     for k, v in dbmod.DOC_TYPES.items()]
        return self.json_response({"departments": deps, "types": types})

    def api_stats(self):
        with dbmod.connect(self.db_path) as conn:
            return self.json_response(searchmod.stats(conn))


def serve(db_path, host="127.0.0.1", port=8000):
    app = OpenDataApp(db_path)
    with make_server(host, port, app,
                     server_class=ThreadingWSGIServer,
                     handler_class=_QuietHandler) as httpd:
        print(f"✔ 服务已启动: http://{host}:{port}  （Ctrl+C 停止）")
        print(f"  数据库: {db_path}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止。")

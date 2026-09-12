#!/usr/bin/env python3
"""单元测试：分词、导入、搜索过滤、相似资料、HTTP API。"""
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.request
from wsgiref.simple_server import make_server

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db as dbmod                       # noqa: E402
from app import search as searchmod               # noqa: E402
from app.server import OpenDataApp                # noqa: E402
from app.tokenizer import tokenize, query_terms   # noqa: E402
from scripts.import_data import import_file, normalize_date  # noqa: E402
from scripts.make_sample_data import DOCS         # noqa: E402

SAMPLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "sample", "documents.json")


class TokenizerTest(unittest.TestCase):
    def test_cjk_bigram(self):
        self.assertEqual(tokenize("公共交通"), "公共 共交 交通")

    def test_mixed(self):
        self.assertEqual(tokenize("GDP增长5.8%"), "gdp 增长 5 8")

    def test_query_terms(self):
        terms = query_terms("交通拥堵")
        self.assertIn("交通拥堵", terms)
        self.assertIn("交通", terms)


class DateTest(unittest.TestCase):
    def test_formats(self):
        for raw in ("2024-3-5", "2024/03/05", "2024.3.5",
                    "2024年3月5日", "20240305", "2024-03-05"):
            self.assertEqual(normalize_date(raw), "2024-03-05", raw)

    def test_invalid(self):
        with self.assertRaises(Exception):
            normalize_date("2024-13-40")


class SearchTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.tmp.name, "test.db")
        import_file(SAMPLE, cls.db_path)
        cls.conn = dbmod.connect(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.tmp.cleanup()


class ImportTest(SearchTestBase):
    def test_counts(self):
        n = self.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        self.assertEqual(n, len(DOCS))
        nf = self.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        self.assertEqual(nf, sum(len(d["files"]) for d in DOCS))

    def test_fts_populated(self):
        n = self.conn.execute("SELECT COUNT(*) FROM docs_fts").fetchone()[0]
        self.assertEqual(n, len(DOCS))

    def test_upsert_idempotent(self):
        import_file(SAMPLE, self.db_path)
        n = self.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        self.assertEqual(n, len(DOCS))


class SearchTest(SearchTestBase):
    def test_keyword(self):
        r = searchmod.search(self.conn, q="交通")
        self.assertGreater(r["total"], 0)
        self.assertTrue(any("交通" in d["title"] or "交通" in d["summary"]
                            for d in r["results"]))

    def test_keyword_multiword(self):
        r = searchmod.search(self.conn, q="停车")
        self.assertGreaterEqual(r["total"], 1)
        ids = [d["id"] for d in r["results"]]
        self.assertIn("POL-2026-003", ids)

    def test_filter_type(self):
        r = searchmod.search(self.conn, q="", doc_type="map")
        self.assertEqual(r["total"], 5)
        self.assertTrue(all(d["doc_type"] == "map" for d in r["results"]))

    def test_filter_department(self):
        r = searchmod.search(self.conn, q="", department="统计局")
        self.assertEqual(r["total"], 3)
        self.assertTrue(all(d["department"] == "统计局" for d in r["results"]))

    def test_filter_date_range(self):
        r = searchmod.search(self.conn, q="", date_from="2024-01-01",
                             date_to="2024-12-31", size=50)
        self.assertGreater(r["total"], 0)
        self.assertTrue(all("2024-01-01" <= d["published_date"] <= "2024-12-31"
                            for d in r["results"]))

    def test_combined(self):
        r = searchmod.search(self.conn, q="空气", doc_type="policy",
                             department="生态环境局")
        self.assertEqual(r["total"], 1)
        self.assertEqual(r["results"][0]["id"], "POL-2024-007")

    def test_empty_query_sorted_by_date(self):
        r = searchmod.search(self.conn, q="", size=50)
        dates = [d["published_date"] for d in r["results"]]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_pagination(self):
        r1 = searchmod.search(self.conn, q="", size=5, page=1)
        r2 = searchmod.search(self.conn, q="", size=5, page=2)
        self.assertEqual(len(r1["results"]), 5)
        self.assertNotEqual({d["id"] for d in r1["results"]},
                            {d["id"] for d in r2["results"]})
        self.assertEqual(r1["pages"], -(-len(DOCS) // 5))

    def test_snippet_highlight(self):
        r = searchmod.search(self.conn, q="停车")
        self.assertIn("<mark>", r["results"][0]["snippet"])

    def test_facets(self):
        r = searchmod.search(self.conn, q="")
        names = {f["name"] for f in r["facets"]["types"]}
        self.assertEqual(names, {"policy", "map", "statistics", "pdf_attachment"})


class DetailTest(SearchTestBase):
    def test_get_document(self):
        doc = searchmod.get_document(self.conn, "POL-2026-003")
        self.assertEqual(doc["type_label"], "政策文件")
        self.assertEqual(len(doc["files"]), 2)
        self.assertEqual(doc["files"][0]["format"], "pdf")

    def test_missing(self):
        self.assertIsNone(searchmod.get_document(self.conn, "NOPE-000"))

    def test_similar(self):
        sims = searchmod.similar_documents(self.conn, "POL-2026-003")
        self.assertGreater(len(sims), 0)
        self.assertNotIn("POL-2026-003", [s["id"] for s in sims])
        # 同部门/同标签的应排在前面
        self.assertTrue(any(s["department"] == "交通运输局" for s in sims[:3]))
        for s in sims:
            self.assertTrue(s["reasons"])


class ApiTest(SearchTestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.httpd = make_server("127.0.0.1", 0, OpenDataApp(cls.db_path))
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        super().tearDownClass()

    def get(self, path, expect=200):
        url = f"http://127.0.0.1:{self.port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                self.assertEqual(resp.status, expect)
                return resp.read().decode("utf-8"), resp.headers
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, expect)
            return e.read().decode("utf-8"), e.headers

    def test_index_page(self):
        body, headers = self.get("/")
        self.assertIn("城市开放资料搜索", body)

    def test_detail_page(self):
        body, _ = self.get("/document/POL-2026-003")
        self.assertIn("停车管理条例", body)
        self.assertIn("文件清单", body)
        self.assertIn("相似资料", body)

    def test_detail_404(self):
        self.get("/document/NOPE-000", expect=404)

    def test_api_search(self):
        body, headers = self.get("/api/search?q=%E4%BA%A4%E9%80%9A&type=policy")
        self.assertIn("application/json", headers["Content-Type"])
        data = json.loads(body)
        self.assertGreater(data["total"], 0)
        self.assertTrue(all(r["doc_type"] == "policy" for r in data["results"]))

    def test_api_search_filters(self):
        body, _ = self.get("/api/search?department=%E7%BB%9F%E8%AE%A1%E5%B1%80"
                           "&date_from=2026-01-01")
        data = json.loads(body)
        self.assertEqual(data["total"], 2)

    def test_api_document(self):
        body, _ = self.get("/api/documents/MAP-2026-001")
        data = json.loads(body)
        self.assertEqual(data["title"].split("（")[0], "市国土空间总体规划")
        self.assertEqual(len(data["files"]), 3)
        self.assertIn("similar", data)

    def test_api_document_404(self):
        self.get("/api/documents/NOPE", expect=404)

    def test_api_similar(self):
        body, _ = self.get("/api/documents/STA-2026-002/similar")
        data = json.loads(body)
        self.assertGreater(len(data["similar"]), 0)

    def test_api_facets_and_stats(self):
        body, _ = self.get("/api/facets")
        self.assertIn("统计局", json.loads(body)["departments"])
        body, _ = self.get("/api/stats")
        data = json.loads(body)
        self.assertEqual(data["documents"], len(DOCS))
        self.assertEqual(data["files"], 39)


if __name__ == "__main__":
    unittest.main(verbosity=2)

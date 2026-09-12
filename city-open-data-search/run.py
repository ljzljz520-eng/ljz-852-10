#!/usr/bin/env python3
"""启动城市开放资料搜索服务。

用法：
    python3 run.py                      # 默认 127.0.0.1:8000，库为空时自动导入示例数据
    python3 run.py --port 8080 --host 0.0.0.0
    python3 run.py --db data/opendata.db
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import db as dbmod            # noqa: E402
from app.server import serve           # noqa: E402
from scripts.import_data import import_file  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description="城市开放资料搜索服务")
    ap.add_argument("--db", default=os.path.join(ROOT, "data", "opendata.db"),
                    help="SQLite 数据库路径（默认 data/opendata.db）")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    conn = dbmod.init_db(args.db)
    count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    conn.close()

    if count == 0:
        sample = os.path.join(ROOT, "data", "sample", "documents.json")
        if os.path.exists(sample):
            print("数据库为空，正在导入示例数据…")
            import_file(sample, args.db)
        else:
            print("提示：数据库为空。可执行以下命令生成并导入示例数据：")
            print("  python3 scripts/make_sample_data.py")
            print(f"  python3 scripts/import_data.py data/sample/documents.json --db {args.db}")

    serve(args.db, args.host, args.port)


if __name__ == "__main__":
    main()

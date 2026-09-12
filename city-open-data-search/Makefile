.PHONY: sample import run test clean

sample:        ## 生成示例数据
	python3 scripts/make_sample_data.py

import:        ## 导入示例数据（重建索引）
	python3 scripts/import_data.py data/sample/documents.json --reset

run:           ## 启动服务 http://127.0.0.1:8000
	python3 run.py

test:          ## 运行单元测试
	python3 -m unittest discover -s tests -v

clean:         ## 删除生成的数据库
	rm -f data/opendata.db

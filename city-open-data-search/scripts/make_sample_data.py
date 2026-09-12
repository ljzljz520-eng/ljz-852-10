#!/usr/bin/env python3
"""生成示例数据：data/sample/documents.json（确定性输出，便于测试与演示）。"""
import hashlib
import json
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "sample", "documents.json")


def f(doc_id, name, fmt, size):
    return {
        "filename": name,
        "format": fmt,
        "size_bytes": size,
        "url": f"https://data.example-city.gov.cn/files/{doc_id}/{name}",
        "checksum": hashlib.md5(f"{doc_id}/{name}".encode()).hexdigest(),
    }


DOCS = [
    # ---------------- 政策文件 ----------------
    dict(id="POL-2026-003", doc_type="policy", department="交通运输局",
         published_date="2026-04-18", tags=["交通", "停车", "收费管理"],
         title="城市机动车停车管理条例（2026 年修订）",
         summary="规范道路停车泊位设置、收费定价与错峰共享机制，明确老旧小区周边夜间限时免费泊位，"
                 "并建立停车设施备案与信息公开制度。",
         content="条例共七章四十二条，涵盖停车规划、建设、运营与执法。新增条款要求公共停车场实时公布空余泊位数据，"
                 "鼓励机关企事业单位停车场夜间向周边居民开放。",
         source_url="https://www.example-city.gov.cn/policy/POL-2026-003",
         files=[f("POL-2026-003", "停车管理条例-2026修订.pdf", "pdf", 1_245_000),
                f("POL-2026-003", "政策解读一图读懂.png", "png", 380_000)]),
    dict(id="POL-2025-011", doc_type="policy", department="教育局",
         published_date="2025-06-30", tags=["教育", "学区", "招生"],
         title="义务教育阶段学校学区划分调整方案（2025 学年）",
         summary="结合新建学校投用与人口流动情况，对主城区 24 所小学、11 所初中的施教区进行微调，"
                 "并公布过渡期入学政策。",
         content="方案遵循就近入学与学位供需平衡原则，附各学区边界文字说明与示意图。"
                 "2025 年 9 月 1 日起执行，设置一年过渡期。",
         source_url="https://www.example-city.gov.cn/policy/POL-2025-011",
         files=[f("POL-2025-011", "学区划分调整方案.pdf", "pdf", 2_860_000),
                f("POL-2025-011", "学区边界示意图.zip", "zip", 15_400_000)]),
    dict(id="POL-2024-007", doc_type="policy", department="生态环境局",
         published_date="2024-03-15", tags=["环境", "空气质量", "减排"],
         title="大气污染防治攻坚行动方案（2024—2025 年）",
         summary="围绕 PM2.5 与臭氧协同控制，部署工业源、移动源、扬尘源治理任务，"
                 "明确到 2025 年空气质量优良天数比率达到 88%。",
         content="方案提出淘汰老旧柴油货车、推进重点行业超低排放改造、强化工地扬尘在线监控等 28 项措施。",
         source_url="https://www.example-city.gov.cn/policy/POL-2024-007",
         files=[f("POL-2024-007", "大气污染防治攻坚行动方案.pdf", "pdf", 1_980_000)]),
    dict(id="POL-2023-002", doc_type="policy", department="住房和城乡建设局",
         published_date="2023-01-20", tags=["住房", "老旧小区", "改造"],
         title="城镇老旧小区改造三年行动计划",
         summary="2023—2025 年计划改造老旧小区 312 个，重点完善水电气路、加装电梯、"
                 "增补停车与养老托育设施。",
         content="计划明确改造内容清单、资金分担机制与居民参与程序，改造方案须经过双三分之二业主同意。",
         source_url="https://www.example-city.gov.cn/policy/POL-2023-002",
         files=[f("POL-2023-002", "老旧小区改造三年行动计划.pdf", "pdf", 2_240_000),
                f("POL-2023-002", "改造小区清单.xlsx", "xlsx", 96_000)]),
    dict(id="POL-2022-014", doc_type="policy", department="卫生健康委员会",
         published_date="2022-11-08", tags=["卫生", "养老", "医疗服务"],
         title="医养结合服务体系建设实施方案",
         summary="推动医疗机构与养老机构签约合作，建设社区医养结合服务中心，"
                 "到 2025 年每千名老年人拥有养老床位 45 张。",
         content="方案包括家庭病床、上门护理、安宁疗护试点等内容，并建立医养结合机构等级评定制度。",
         source_url="https://www.example-city.gov.cn/policy/POL-2022-014",
         files=[f("POL-2022-014", "医养结合实施方案.pdf", "pdf", 1_560_000)]),

    # ---------------- 地图 ----------------
    dict(id="MAP-2026-001", doc_type="map", department="自然资源和规划局",
         published_date="2026-02-10", tags=["地图", "国土空间", "规划"],
         title="市国土空间总体规划（2021—2035 年）成果图集",
         summary="包含市域国土空间总体格局、生态保护红线、永久基本农田、城镇开发边界等"
                 "法定规划成果图件 42 幅。",
         content="图集提供在线浏览与 GeoJSON/Shapefile 矢量数据下载，坐标系为 CGCS2000。",
         source_url="https://www.example-city.gov.cn/map/MAP-2026-001",
         files=[f("MAP-2026-001", "国土空间规划图集.pdf", "pdf", 48_600_000),
                f("MAP-2026-001", "三条控制线.shp.zip", "zip", 8_900_000),
                f("MAP-2026-001", "规划分区.geojson", "geojson", 2_300_000)]),
    dict(id="MAP-2025-006", doc_type="map", department="交通运输局",
         published_date="2025-09-01", tags=["地图", "交通", "地铁", "公交"],
         title="城市轨道交通线网运营图（2025 年版）",
         summary="收录已运营地铁线路 9 条、站点 198 座及与公交枢纽、火车站的换乘关系，"
                 "提供无障碍设施标注。",
         content="随 5 号线二期开通同步更新，附首末班车时刻与线网票价图。",
         source_url="https://www.example-city.gov.cn/map/MAP-2025-006",
         files=[f("MAP-2025-006", "轨道交通线网图-2025.pdf", "pdf", 6_720_000),
                f("MAP-2025-006", "站点列表.csv", "csv", 88_000)]),
    dict(id="MAP-2024-009", doc_type="map", department="文化和旅游局",
         published_date="2024-08-16", tags=["地图", "旅游", "公共文化"],
         title="全域旅游导览图与公共文化设施分布图",
         summary="标注 A 级景区、博物馆、图书馆、文化馆、城市书房等设施点位与开放信息，"
                 "支持扫码导航。",
         content="数据每季度更新，提供在线地图与开放 API 接口。",
         source_url="https://www.example-city.gov.cn/map/MAP-2024-009",
         files=[f("MAP-2024-009", "全域旅游导览图.pdf", "pdf", 12_300_000),
                f("MAP-2024-009", "文化设施点位.csv", "csv", 210_000)]),
    dict(id="MAP-2023-004", doc_type="map", department="住房和城乡建设局",
         published_date="2023-05-22", tags=["地图", "绿地", "公园"],
         title="城市公园绿地服务半径覆盖分析图",
         summary="基于 500 米服务半径分析建成区公园绿地覆盖情况，识别覆盖盲区 17 处，"
                 "为绿地系统规划提供依据。",
         content="分析采用 2022 年国土变更调查数据与人口网格数据。",
         source_url="https://www.example-city.gov.cn/map/MAP-2023-004",
         files=[f("MAP-2023-004", "公园绿地覆盖分析图.pdf", "pdf", 9_150_000),
                f("MAP-2023-004", "覆盖盲区.shp.zip", "zip", 1_100_000)]),
    dict(id="MAP-2022-002", doc_type="map", department="生态环境局",
         published_date="2022-07-19", tags=["地图", "噪声", "环境"],
         title="中心城区声环境功能区划图",
         summary="划定 0—4 类声环境功能区，明确各区域昼夜噪声限值，"
                 "作为噪声执法与规划环评依据。",
         content="区划图随城市开发边界调整每五年修订一次。",
         source_url="https://www.example-city.gov.cn/map/MAP-2022-002",
         files=[f("MAP-2022-002", "声环境功能区划图.pdf", "pdf", 7_480_000)]),

    # ---------------- 统计表 ----------------
    dict(id="STA-2026-002", doc_type="statistics", department="统计局",
         published_date="2026-03-05", tags=["统计", "人口", "年度"],
         title="2025 年国民经济和社会发展统计公报",
         summary="公布 2025 年全市常住人口、GDP、产业结构、居民收入、教育卫生等"
                 "核心统计数据。",
         content="2025 年末常住人口 1286.4 万人，地区生产总值 2.41 万亿元，"
                 "城镇居民人均可支配收入 78 432 元。",
         source_url="https://www.example-city.gov.cn/stats/STA-2026-002",
         files=[f("STA-2026-002", "2025统计公报.pdf", "pdf", 3_260_000),
                f("STA-2026-002", "主要指标.xlsx", "xlsx", 145_000),
                f("STA-2026-002", "分区县数据.csv", "csv", 96_000)]),
    dict(id="STA-2025-008", doc_type="statistics", department="统计局",
         published_date="2025-04-11", tags=["统计", "季度", "经济"],
         title="2025 年一季度经济运行情况统计表",
         summary="包含地区生产总值、规上工业增加值、固定资产投资、社会消费品零售总额等"
                 "季度指标及增速。",
         content="一季度 GDP 同比增长 5.8%，高技术制造业增加值增长 12.3%。",
         source_url="https://www.example-city.gov.cn/stats/STA-2025-008",
         files=[f("STA-2025-008", "2025Q1经济运行统计表.xlsx", "xlsx", 78_000),
                f("STA-2025-008", "指标说明.pdf", "pdf", 420_000)]),
    dict(id="STA-2024-012", doc_type="statistics", department="教育局",
         published_date="2024-10-25", tags=["统计", "教育", "学校"],
         title="2023—2024 学年教育事业统计年报",
         summary="汇总各级各类学校数量、在校生数、专任教师数、大班额比例等教育统计指标。",
         content="全市共有中小学 862 所，在校生 132.6 万人，义务教育巩固率 99.4%。",
         source_url="https://www.example-city.gov.cn/stats/STA-2024-012",
         files=[f("STA-2024-012", "教育事业统计年报.xlsx", "xlsx", 320_000),
                f("STA-2024-012", "分学校明细.csv", "csv", 1_840_000)]),
    dict(id="STA-2024-005", doc_type="statistics", department="卫生健康委员会",
         published_date="2024-06-14", tags=["统计", "卫生", "医疗资源"],
         title="2023 年医疗卫生资源与医疗服务统计表",
         summary="公布医疗卫生机构数、床位数、执业（助理）医师数、总诊疗人次等年度数据。",
         content="全市医疗卫生机构 5 214 个，实有床位 9.8 万张，年总诊疗 1.62 亿人次。",
         source_url="https://www.example-city.gov.cn/stats/STA-2024-005",
         files=[f("STA-2024-005", "卫生统计表-2023.xlsx", "xlsx", 156_000)]),
    dict(id="STA-2023-010", doc_type="statistics", department="生态环境局",
         published_date="2023-04-28", tags=["统计", "空气质量", "环境监测"],
         title="2022 年环境质量状况统计表",
         summary="包含空气质量六项污染物年均浓度、优良天数、地表水断面水质、"
                 "声环境监测结果。",
         content="2022 年 PM2.5 年均浓度 32 微克/立方米，空气质量优良天数比率 85.2%。",
         source_url="https://www.example-city.gov.cn/stats/STA-2023-010",
         files=[f("STA-2023-010", "环境质量统计-2022.xlsx", "xlsx", 132_000),
                f("STA-2023-010", "监测点位.csv", "csv", 64_000)]),
    dict(id="STA-2022-006", doc_type="statistics", department="交通运输局",
         published_date="2022-09-30", tags=["统计", "交通", "出行"],
         title="2021 年居民出行调查主要数据公报",
         summary="公布居民日均出行次数、出行方式结构、通勤时耗等调查结果，"
                 "为交通规划提供基础数据。",
         content="全市居民日均出行 2.31 次，公共交通分担率 38.6%，平均通勤时间 39 分钟。",
         source_url="https://www.example-city.gov.cn/stats/STA-2022-006",
         files=[f("STA-2022-006", "居民出行调查公报.pdf", "pdf", 2_050_000),
                f("STA-2022-006", "交叉分析表.xlsx", "xlsx", 268_000)]),

    # ---------------- PDF 附件（元数据） ----------------
    dict(id="PDF-2026-001", doc_type="pdf_attachment", department="统计局",
         published_date="2026-01-15", tags=["PDF附件", "人口", "普查"],
         title="第七次全国人口普查主要数据公报（本市卷）PDF 附件",
         summary="人口普查公报 PDF 原件元数据：含总人口、年龄结构、受教育程度、"
                 "城乡分布等章节，共 46 页。",
         content="附件由统计局普查中心扫描归档，分辨率 300dpi，已做 OCR 文字识别，可全文检索。",
         source_url="https://www.example-city.gov.cn/attach/PDF-2026-001",
         files=[f("PDF-2026-001", "人口普查公报-本市卷.pdf", "pdf", 18_700_000)]),
    dict(id="PDF-2025-004", doc_type="pdf_attachment", department="自然资源和规划局",
         published_date="2025-05-20", tags=["PDF附件", "规划", "公示"],
         title="控制性详细规划公示图纸 PDF 附件包（2025 年第二批）",
         summary="收录 12 个街坊控规公示图纸 PDF，含用地布局图、图则与公示说明，"
                 "公示期 30 天。",
         content="附件按街坊编号命名，公示意见反馈渠道见公示说明末页。",
         source_url="https://www.example-city.gov.cn/attach/PDF-2025-004",
         files=[f("PDF-2025-004", "A-03街坊控规图则.pdf", "pdf", 5_600_000),
                f("PDF-2025-004", "B-11街坊控规图则.pdf", "pdf", 4_900_000),
                f("PDF-2025-004", "公示说明.pdf", "pdf", 780_000)]),
    dict(id="PDF-2024-003", doc_type="pdf_attachment", department="住房和城乡建设局",
         published_date="2024-09-09", tags=["PDF附件", "住房", "保障房"],
         title="公共租赁住房保障资格审核结果公示 PDF 附件（2024 年第九批）",
         summary="公示 2024 年第九批公租房资格审核通过家庭名单及轮候顺序，"
                 "PDF 原件含异议反馈方式。",
         content="公示期 7 个工作日，名单已做身份证号脱敏处理。",
         source_url="https://www.example-city.gov.cn/attach/PDF-2024-003",
         files=[f("PDF-2024-003", "公租房资格审核公示-第9批.pdf", "pdf", 2_340_000)]),
    dict(id="PDF-2023-008", doc_type="pdf_attachment", department="生态环境局",
         published_date="2023-12-01", tags=["PDF附件", "环评", "公示"],
         title="重点建设项目环境影响报告书批复 PDF 附件汇编（2023 年度）",
         summary="汇编 2023 年度 36 个重点项目环评批复文件 PDF 扫描件，"
                 "按项目编号排序并附索引目录。",
         content="附件来源于行政审批档案数字化成果，可供公众依申请查阅原件。",
         source_url="https://www.example-city.gov.cn/attach/PDF-2023-008",
         files=[f("PDF-2023-008", "环评批复汇编-2023.pdf", "pdf", 62_400_000),
                f("PDF-2023-008", "项目索引.csv", "csv", 18_000)]),
    dict(id="PDF-2022-005", doc_type="pdf_attachment", department="文化和旅游局",
         published_date="2022-04-27", tags=["PDF附件", "文物", "保护"],
         title="市级文物保护单位名录及保护范围图则 PDF 附件",
         summary="收录 128 处市级文物保护单位名录、简介与保护范围图则 PDF，"
                 "含建设控制地带说明。",
         content="图则按 1:2000 比例尺绘制，可与国土空间规划一张图叠加使用。",
         source_url="https://www.example-city.gov.cn/attach/PDF-2022-005",
         files=[f("PDF-2022-005", "文保单位名录.pdf", "pdf", 9_860_000),
                f("PDF-2022-005", "保护范围图则.pdf", "pdf", 34_500_000)]),
]


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(DOCS, fh, ensure_ascii=False, indent=2)
    n_files = sum(len(d["files"]) for d in DOCS)
    print(f"✔ 已生成 {OUT}：{len(DOCS)} 条资料，{n_files} 个附件")


if __name__ == "__main__":
    main()

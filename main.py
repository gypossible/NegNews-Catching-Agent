#!/usr/bin/env python3
"""
NegNews-Catching Agent
用法: python main.py <excel文件路径>

对 Excel 每个 sheet 的 B 列主体名称，搜索近一年内的负面舆情
（债券违约、商票逾期、失信被执行、欠税），结果写入 C 列起的各单元格。
"""

import sys
import config
from modules.excel_handler import load_workbook, iter_entities, save_workbook
from modules.result_writer import write_results
from modules.searchers.baidu_searcher import BaiduSearcher
from modules.searchers.sina_searcher import SinaSearcher
from modules.searchers.court_searcher import CourtSearcher
from modules.searchers.qichacha_searcher import QiChaChaSearcher
from utils.http_client import build_session


def deduplicate(results: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for r in results:
        key = r.get("url", "") or r.get("title", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def main(input_path: str) -> None:
    print(f"[开始] 加载文件: {input_path}")
    wb = load_workbook(input_path)
    session = build_session()

    searchers = [
        BaiduSearcher(session, config),
        SinaSearcher(session, config),
        CourtSearcher(session, config),
        QiChaChaSearcher(session, config),
    ]

    for sheet, row_idx, entity in iter_entities(wb):
        print(f"\n[搜索] Sheet={sheet.title!r}  行={row_idx}  主体={entity!r}")
        all_results = []

        for keyword in config.KEYWORDS:
            for searcher in searchers:
                try:
                    results = searcher.search(entity, keyword)
                    if results:
                        print(f"  {searcher.__class__.__name__} [{keyword}]: {len(results)} 条")
                    all_results.extend(results)
                except Exception as e:
                    print(f"  [WARN] {searcher.__class__.__name__} 异常 ({keyword}): {e}")

        unique = deduplicate(all_results)[: config.MAX_RESULTS_PER_ENTITY]
        write_results(sheet, row_idx, unique)
        print(f"  => 写入 {len(unique)} 条结果")

    save_workbook(wb, input_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python main.py <excel文件路径>")
        sys.exit(1)
    main(sys.argv[1])

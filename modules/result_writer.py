from openpyxl.worksheet.worksheet import Worksheet
import config


def format_result(r: dict) -> str:
    """将结果字典格式化为单元格字符串。"""
    return f"[{r['source']}] {r.get('date', '')} | {r.get('title', '')} | {r.get('url', '')}"


def write_results(sheet: Worksheet, row_idx: int, results: list[dict]) -> None:
    """从 C 列开始，每条结果写入一个单元格。"""
    for i, result in enumerate(results):
        col = config.OUTPUT_START_COL + i
        sheet.cell(row=row_idx, column=col, value=format_result(result))

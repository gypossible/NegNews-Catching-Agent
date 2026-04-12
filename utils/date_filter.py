import re
from datetime import datetime, timedelta

CUTOFF = datetime.now() - timedelta(days=365)

# 常见中文日期格式
_DATE_PATTERNS = [
    r"(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})",   # 2024年3月5日 / 2024-03-05
    r"(\d{4})(\d{2})(\d{2})",                        # 20240305
]


def parse_date(text: str) -> datetime | None:
    if not text:
        return None
    for pattern in _DATE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
    return None


def is_within_range(date_text: str, cutoff: datetime = CUTOFF) -> bool:
    """返回 True 表示日期在近一年内（或无法解析日期时默认保留）。"""
    dt = parse_date(date_text)
    if dt is None:
        return True  # 无法解析则保留，避免漏掉有效结果
    return dt >= cutoff

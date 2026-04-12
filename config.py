from datetime import datetime, timedelta

# 搜索关键词
KEYWORDS = [
    "债券违约",
    "商票逾期",
    "失信被执行",
    "欠税",
]

# 时间范围：近一年
TIME_RANGE_DAYS = 365
CUTOFF_DATE = datetime.now() - timedelta(days=TIME_RANGE_DAYS)

# Excel 列配置（openpyxl 1-based）
ENTITY_COL = 2          # B 列：主体名称
OUTPUT_START_COL = 3    # C 列开始写入结果
HEADER_ROW = 1          # 第1行为表头
DATA_START_ROW = 2      # 第2行开始为数据

# 每个主体最多写入结果数
MAX_RESULTS_PER_ENTITY = 10

# 请求间隔（秒），随机范围
REQUEST_DELAY = (2, 5)

from bs4 import BeautifulSoup
from .base_searcher import BaseSearcher
from utils.http_client import get
from utils.date_filter import is_within_range

SINA_SEARCH_URL = "https://search.sina.com.cn/"


class SinaSearcher(BaseSearcher):
    """新浪财经搜索。"""

    def search(self, entity: str, keyword: str) -> list[dict]:
        params = {
            "q": f'"{entity}" {keyword}',
            "range": "all",
            "c": "news",
            "sort": "time",
            "num": "10",
        }
        try:
            resp = get(self.session, SINA_SEARCH_URL, params=params,
                       delay=self.config.REQUEST_DELAY)
            resp.raise_for_status()
            resp.encoding = "utf-8"
        except Exception as e:
            print(f"  [新浪] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        results = []

        for item in soup.select(".box-result") or soup.select(".result-item"):
            title_tag = item.select_one("h2 a") or item.select_one("a.title")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            url = title_tag.get("href", "")

            date_tag = item.select_one(".fgray_time") or item.select_one(".time")
            date_text = date_tag.get_text(strip=True) if date_tag else ""

            if not is_within_range(date_text):
                continue

            results.append({
                "source": "新浪财经",
                "title": title,
                "date": date_text,
                "url": url,
            })

        return results

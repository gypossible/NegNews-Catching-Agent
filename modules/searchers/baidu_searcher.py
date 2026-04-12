from bs4 import BeautifulSoup
from .base_searcher import BaseSearcher
from utils.http_client import get
from utils.date_filter import is_within_range

BAIDU_NEWS_URL = "https://news.baidu.com/ns"


class BaiduSearcher(BaseSearcher):
    """百度新闻搜索。"""

    def search(self, entity: str, keyword: str) -> list[dict]:
        params = {
            "word": f'"{entity}" {keyword}',
            "tn": "news",
            "rn": "10",
            "cl": "2",
            "ie": "utf-8",
        }
        headers = {
            "Referer": "https://www.baidu.com",
        }
        try:
            resp = get(self.session, BAIDU_NEWS_URL, params=params,
                       delay=self.config.REQUEST_DELAY, headers=headers)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [百度] 请求失败: {e}")
            return []

        # 检测是否触发验证码
        if "百度安全验证" in resp.text or "captcha" in resp.url:
            print(f"  [百度] 触发验证码，跳过: {entity}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        results = []

        for item in soup.select(".result"):
            title_tag = item.select_one("h3 a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            url = title_tag.get("href", "")

            # 日期：多种可能的 class
            date_tag = (
                item.select_one(".c-color-gray2")
                or item.select_one(".c-gap-top-small")
                or item.select_one("p.c-author")
            )
            date_text = date_tag.get_text(strip=True) if date_tag else ""

            if not is_within_range(date_text):
                continue

            results.append({
                "source": "百度新闻",
                "title": title,
                "date": date_text,
                "url": url,
            })

        return results

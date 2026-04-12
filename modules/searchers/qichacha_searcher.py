import os
from bs4 import BeautifulSoup
from .base_searcher import BaseSearcher
from utils.http_client import get

QCC_SEARCH_URL = "https://www.qichacha.com/search"


class QiChaChaSearcher(BaseSearcher):
    """
    企查查搜索（best-effort）。
    需要在环境变量 QCC_COOKIE 中提供从浏览器复制的 Cookie 字符串。
    未设置时自动跳过，不影响整体运行。
    """

    def search(self, entity: str, keyword: str) -> list[dict]:
        cookie = os.environ.get("QCC_COOKIE", "").strip()
        if not cookie:
            return []  # 未配置 cookie，静默跳过

        headers = {
            "Cookie": cookie,
            "Referer": "https://www.qichacha.com/",
        }
        params = {"key": entity}

        try:
            resp = get(self.session, QCC_SEARCH_URL, params=params,
                       delay=self.config.REQUEST_DELAY, headers=headers)
            resp.raise_for_status()
            resp.encoding = "utf-8"
        except Exception as e:
            print(f"  [企查查] 请求失败: {e}")
            return []

        # 检测登录墙
        if "请登录" in resp.text or "login" in resp.url:
            print(f"  [企查查] Cookie 已过期或被拦截，跳过: {entity}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        results = []

        # 企查查搜索结果结构可能变化，尝试提取风险相关条目
        for item in soup.select(".m-risk-item") or soup.select(".risk-item"):
            title_tag = item.select_one("a") or item.select_one(".title")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            url = title_tag.get("href", "https://www.qichacha.com")
            if not url.startswith("http"):
                url = "https://www.qichacha.com" + url

            date_tag = item.select_one(".date") or item.select_one(".time")
            date_text = date_tag.get_text(strip=True) if date_tag else ""

            results.append({
                "source": "企查查",
                "title": title,
                "date": date_text,
                "url": url,
            })

        return results

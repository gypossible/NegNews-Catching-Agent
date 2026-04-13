import os
import hashlib
import time
import requests
from .base_searcher import BaseSearcher
from utils.date_filter import is_within_range

# 企查查开放平台 API
# 文档: https://openapi.qichacha.com
QCC_BASE = "https://api.qichacha.com"


def _sign(app_key: str, secret_key: str) -> tuple[str, str]:
    """生成企查查 API 签名，返回 (timespan, token)。"""
    timespan = str(int(time.time()))
    raw = app_key + timespan + secret_key
    token = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return timespan, token


class QiChaChaSearcher(BaseSearcher):
    """
    企查查开放平台 API 搜索。
    需要环境变量:
      QCC_APP_KEY   — 企查查 AppKey（手机号）
      QCC_SECRET    — 企查查 SecretKey
    未设置时自动跳过。
    """

    def search(self, entity: str, keyword: str) -> list[dict]:
        app_key = os.environ.get("QCC_APP_KEY", "").strip()
        secret = os.environ.get("QCC_SECRET", "").strip()
        if not app_key or not secret:
            return []

        timespan, token = _sign(app_key, secret)
        headers = {
            "Token": token,
            "Timespan": timespan,
            "AppKey": app_key,
        }

        results = []

        # 1. 失信被执行 — 司法风险
        if "失信" in keyword:
            results += self._fetch_dishonest(entity, headers)

        # 2. 欠税 — 经营风险
        if "欠税" in keyword:
            results += self._fetch_tax(entity, headers)

        # 3. 债券/商票 — 用企查查新闻舆情接口
        if keyword in ("债券违约", "商票逾期"):
            results += self._fetch_news(entity, keyword, headers)

        return results

    def _fetch_dishonest(self, entity: str, headers: dict) -> list[dict]:
        url = f"{QCC_BASE}/ECIExecInfo/GetList"
        try:
            resp = requests.get(url, params={"keyword": entity, "pageIndex": 1},
                                headers=headers, timeout=15)
            data = resp.json()
        except Exception as e:
            print(f"  [企查查-失信] 请求失败: {e}")
            return []

        items = data.get("Data", {}).get("Result", []) or []
        out = []
        for item in items:
            date_text = item.get("PunishmentDate", "")
            if not is_within_range(date_text):
                continue
            out.append({
                "source": "企查查-失信被执行",
                "title": f"失信被执行: {item.get('iname', entity)} | 案号: {item.get('CaseCode', '')}",
                "date": date_text,
                "url": f"https://www.qichacha.com/firm_{entity}.html",
            })
        return out

    def _fetch_tax(self, entity: str, headers: dict) -> list[dict]:
        url = f"{QCC_BASE}/ECIOweTax/GetList"
        try:
            resp = requests.get(url, params={"keyword": entity, "pageIndex": 1},
                                headers=headers, timeout=15)
            data = resp.json()
        except Exception as e:
            print(f"  [企查查-欠税] 请求失败: {e}")
            return []

        items = data.get("Data", {}).get("Result", []) or []
        out = []
        for item in items:
            date_text = item.get("PublishDate", "")
            if not is_within_range(date_text):
                continue
            out.append({
                "source": "企查查-欠税",
                "title": f"欠税公告: {item.get('TaxpayerName', entity)} | 金额: {item.get('TaxAmount', '')}",
                "date": date_text,
                "url": f"https://www.qichacha.com/firm_{entity}.html",
            })
        return out

    def _fetch_news(self, entity: str, keyword: str, headers: dict) -> list[dict]:
        url = f"{QCC_BASE}/ECINews/GetList"
        try:
            resp = requests.get(url, params={"keyword": f"{entity} {keyword}", "pageIndex": 1},
                                headers=headers, timeout=15)
            data = resp.json()
        except Exception as e:
            print(f"  [企查查-舆情] 请求失败: {e}")
            return []

        items = data.get("Data", {}).get("Result", []) or []
        out = []
        for item in items:
            date_text = item.get("PublishTime", "")
            if not is_within_range(date_text):
                continue
            out.append({
                "source": "企查查-舆情",
                "title": item.get("Title", ""),
                "date": date_text,
                "url": item.get("Url", "https://www.qichacha.com"),
            })
        return out

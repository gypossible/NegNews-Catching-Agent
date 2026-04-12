from .base_searcher import BaseSearcher
from utils.http_client import post, get
from utils.date_filter import is_within_range

COURT_HOME = "https://zxgk.court.gov.cn/zhzxgk/"
COURT_API = "https://zxgk.court.gov.cn/zhzxgk/queryList.do"


class CourtSearcher(BaseSearcher):
    """
    执行信息公开网（zxgk.court.gov.cn）——失信被执行人查询。
    使用官方公开 API，无需登录。
    """

    def search(self, entity: str, keyword: str = "失信被执行") -> list[dict]:
        # 先访问首页获取 session cookie
        try:
            get(self.session, COURT_HOME, delay=(1, 2))
        except Exception:
            pass

        payload = {
            "pName": entity,
            "pCardNum": "",
            "pProvince": "0",
            "currentPage": "1",
        }
        try:
            resp = post(self.session, COURT_API, data=payload,
                        delay=self.config.REQUEST_DELAY)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  [执行信息公开网] 请求失败: {e}")
            return []

        items = data.get("result", {}).get("items", []) or []
        results = []

        for item in items:
            reg_date = item.get("regDate", "")
            if not is_within_range(reg_date):
                continue
            case_code = item.get("caseCode", "")
            court = item.get("courtName", "")
            results.append({
                "source": "执行信息公开网",
                "title": f"失信被执行人: {entity} | 案号: {case_code} | 法院: {court}",
                "date": reg_date,
                "url": "https://zxgk.court.gov.cn",
            })

        return results

from abc import ABC, abstractmethod
import requests


class BaseSearcher(ABC):
    def __init__(self, session: requests.Session, config):
        self.session = session
        self.config = config

    @abstractmethod
    def search(self, entity: str, keyword: str) -> list[dict]:
        """
        搜索指定主体的负面舆情。
        返回 list of dict: {source, title, date, url}
        """
        pass

from abc import ABC, abstractmethod

class BaseCrawler(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.source_name = config.get("name")

    @abstractmethod
    def fetch_job_list(self, target_count: int) -> list:
        """Thu thập danh sách URL hoặc danh sách tóm tắt"""
        pass

    @abstractmethod
    def fetch_job_details(self, job_items: list) -> list:
        """Cào chi tiết và map sang chuẩn JobDetailRaw"""
        pass

    def run(self, target_count: int = 50):
        items = self.fetch_job_list(target_count)
        details = self.fetch_job_details(items)
        self.save(details)

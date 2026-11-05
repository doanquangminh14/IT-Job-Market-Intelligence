"""Phân loại tin tuyển dụng thuộc lĩnh vực IT hay không (phục vụ lọc nhiễu cho CBF)."""
import re
from typing import Iterable, Union

# Chức danh/từ khóa đặc trưng của nghề IT
IT_TITLE_PATTERN = re.compile(
    r"(develop|engineer|lập trình|programmer|software|phần mềm|backend|back-end|front-?end|"
    r"full-?stack|devops|devsecops|\bsre\b|tester|\bqa\b|\bqc\b|kiểm thử|automation|\bdata\b|"
    r"dữ liệu|\bai\b|\bml\b|machine learning|nlp|deep learning|computer vision|blockchain|web3|"
    r"solidity|security|an ninh mạng|an toàn thông tin|pentest|\bsoc\b|dfir|system|hệ thống|"
    r"network|mạng|sysadmin|infrastructure|cloud|\baws\b|azure|database|\bdba\b|\bdev\b|\bit\b|"
    r"công nghệ thông tin|cntt|\bbi\b|business analyst|phân tích nghiệp vụ|\bba\b|product owner|"
    r"scrum|tech lead|technical|solution|architect|\berp\b|\bsap\b|abap|odoo|salesforce|"
    r"\.net|java|python|php|golang|\bgo\b|node|react|angular|vue|flutter|android|\bios\b|mobile|"
    r"unity|embedded|firmware|\biot\b|fpga|\bsql\b|\betl\b|crawler|scraper|helpdesk|help desk|"
    r"it support|technical support|ui/ux|ux/ui|\bux\b|\bui\b|bridge se|\bbrse\b|\bse\b|"
    r"wordpress|shopify|magento|\brpa\b|low-?code|power bi|tableau|analyst|\bcto\b|"
    r"triển khai|game dev|game programmer|technical artist|ux/?ui|product manager|kỹ sư|it project|it - phần mềm)",
    re.IGNORECASE,
)

# Kỹ năng công nghệ lõi: có >= 2 kỹ năng này thì coi là việc IT dù tiêu đề mơ hồ
CORE_IT_SKILLS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "php", "golang", "ruby", "rust",
    "kotlin", "swift", "dart", "sql", "mysql", "postgresql", "mongodb", "redis", "sql server",
    "react", "vue", "angular", "node.js", ".net", "spring boot", "django", "laravel", "flutter",
    "docker", "kubernetes", "aws", "azure", "gcp", "linux", "git", "ci/cd", "html/css",
    "rest api", "microservices", "selenium", "machine learning", "deep learning", "apache spark",
    "apache kafka", "apache airflow", "etl", "android", "ios", "terraform", "jenkins",
}


def _skill_list(skills: Union[str, Iterable[str], None]) -> list:
    if skills is None or isinstance(skills, float):  # None hoặc NaN
        return []
    if isinstance(skills, str):
        return [s.strip().lower() for s in skills.split(",") if s.strip()]
    return [str(s).strip().lower() for s in skills if str(s).strip()]


def is_it_job(title: str, required_skills: Union[str, Iterable[str], None] = None, min_core_skills: int = 2) -> bool:
    """True nếu tiêu đề mang tính IT hoặc có >= min_core_skills kỹ năng công nghệ lõi."""
    if title and IT_TITLE_PATTERN.search(str(title)):
        return True
    return len(set(_skill_list(required_skills)) & CORE_IT_SKILLS) >= min_core_skills

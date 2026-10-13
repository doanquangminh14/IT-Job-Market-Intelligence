import re
from datetime import datetime
import pandas as pd
from .skills import SKILLS_TAXONOMY

def get_skill_patterns():
    """
    Tập hợp biểu thức chính quy tối ưu cho từng kỹ năng trong danh mục 76 kỹ năng.
    Xử lý đặc biệt các trường hợp biên như C#, C++, .NET, Spring Boot, Golang, CI/CD...
    """
    patterns = {
        "Java": r"\bjava\b(?!script)",
        "JavaScript": r"\bjavascript\b|\bjs\b",
        "TypeScript": r"\btypescript\b|\bts\b",
        "C++": r"(?:\bc\+\+(?!\w)|\bcpp\b)",
        "C#": r"(?:\bc#(?!\w)|\bcsharp\b)",
        "Golang": r"(?:\bgolang\b|\bgo\s*(?:developer|dev|engineer|backend|lang|language)\b)",
        "PHP": r"\bphp\b",
        "Python": r"\bpython\b",
        "Ruby": r"\bruby\b",
        "Kotlin": r"\bkotlin\b",
        "Swift": r"\bswift\b",
        "Rust": r"\brust\b",
        "Dart": r"\bdart\b",
        "Scala": r"\bscala\b",
        "HTML/CSS": r"(?:\bhtml5?\b|\bcss3?\b)",
        "React": r"(?:\breact\b(?!\s*native)|\breactjs\b)",
        "Vue.js": r"(?:\bvue(?:\.js|js)?\b)",
        "Angular": r"\bangular(?:\.js|js)?\b",
        "Next.js": r"(?:\bnext(?:\.js|js)?\b)",
        "Tailwind CSS": r"(?:\btailwind(?:\s*css)?\b)",
        "Nuxt.js": r"(?:\bnuxt(?:\.js|js)?\b)",
        "Redux": r"\bredux\b",
        "Node.js": r"(?:\bnode(?:\.js|js)?\b)",
        "Spring Boot": r"(?:\bspring\s*boot\b|\bspring\s*framework\b|\bspring\b)",
        ".NET": r"(?:(?<!\w)\.net\b|\basp\.net\b|\bdotnet\b)",
        "Django": r"\bdjango\b",
        "FastAPI": r"\bfastapi\b",
        "Flask": r"\bflask\b",
        "Laravel": r"\blaravel\b",
        "Express.js": r"(?:\bexpress(?:\.js|js)?\b)",
        "NestJS": r"(?:\bnest(?:\.js|js)?\b)",
        "Ruby on Rails": r"(?:\bruby\s+on\s+rails\b|\brails\b)",
        "SQL": r"\bsql\b",
        "PostgreSQL": r"(?:\bpostgres\b|\bpostgresql\b)",
        "MySQL": r"\bmysql\b",
        "MongoDB": r"\bmongodb\b|\bmongo\b",
        "Redis": r"\bredis\b",
        "Oracle": r"\boracle(?:\s*db|\s*database)?\b",
        "SQL Server": r"(?:\bsql\s*server\b|\bmssql\b)",
        "Elasticsearch": r"(?:\belasticsearch\b|\belastic\s*search\b)",
        "Docker": r"\bdocker\b",
        "Kubernetes": r"(?:\bkubernetes\b|\bk8s\b)",
        "AWS": r"(?:\baws\b|\bamazon\s*web\s*services\b)",
        "Azure": r"(?:\bazure\b)",
        "GCP": r"(?:\bgcp\b|\bgoogle\s*cloud(?:\s*platform)?\b)",
        "CI/CD": r"(?:\bci\s*/\s*cd\b|\bcicd\b)",
        "Linux": r"\blinux\b",
        "Terraform": r"\bterraform\b",
        "Ansible": r"\bansible\b",
        "Machine Learning": r"(?:\bmachine\s*learning\b|\bml\b)",
        "Deep Learning": r"(?:\bdeep\s*learning\b|\bdl\b)",
        "PyTorch": r"\bpytorch\b",
        "TensorFlow": r"\btensorflow\b",
        "NLP": r"(?:\bnlp\b|\bnatural\s*language\s*processing\b)",
        "Computer Vision": r"(?:\bcomputer\s*vision\b|\bcv\b(?!\s*(?:tuyển|ứng)))",
        "LLM": r"(?:\bllm\b|\bgenerative\s*ai\b|\bgenai\b|\brag\b|\blarge\s*language\s*model\b)",
        "Pandas": r"\bpandas\b",
        "NumPy": r"\bnumpy\b",
        "Spark": r"(?:\bspark\b|\bpyspark\b|\bapache\s*spark\b)",
        "Kafka": r"(?:\bkafka\b|\bapache\s*kafka\b)",
        "React Native": r"\breact\s*native\b",
        "Flutter": r"\bflutter\b",
        "Android": r"\bandroid\b",
        "iOS": r"\bios\b",
        "Manual Testing": r"(?:\bmanual\s*test(?:ing)?\b|\bkiểm\s*thử\s*thủ\s*công\b)",
        "Automation Testing": r"(?:\bautomation\s*test(?:ing)?\b|\bauto\s*test(?:ing)?\b|\bkiểm\s*thử\s*tự\s*động\b)",
        "Selenium": r"\bselenium\b",
        "Postman": r"\bpostman\b",
        "JMeter": r"\bjmeter\b",
        "Cypress": r"\bcypress\b",
        "Microservices": r"(?:\bmicroservices?\b|\bkiến\s*trúc\s*microservice\b)",
        "Security": r"(?:\bsecurity\b|\ban\s*ninh\s*mạng\b|\bbảo\s*mật\s*thông\s*tin\b|\bcybersecurity\b)",
        "OAuth": r"(?:\boauth2?\.?0?\b|\bopenid\b)",
        "Git": r"\bgit\b(?!lab|hub)",
        "Agile/Scrum": r"(?:\bagile\b|\bscrum\b)",
        "Jira": r"\bjira\b"
    }
    return patterns

def check_is_preferred(context_text):
    """Kiểm tra ngữ cảnh trích xuất có chứa từ khóa mang tính ưu tiên/điểm cộng hay không."""
    if not context_text:
        return False
    s = str(context_text).lower()
    pref_terms = [
        "ưu tiên", "uu tien", "lợi thế", "loi the", "plus",
        "nice to have", "preferred", "điểm cộng", "không bắt buộc"
    ]
    return any(term in s for term in pref_terms)

def transform_job_skills(bronze_data):
    """
    Trích xuất quan hệ N-N giữa tin việc làm và kỹ năng chuẩn hóa (job_skills).
    Quy trình phân tầng ưu tiên (Multi-layer extraction):
      1. tag_direct (Độ tin cậy 1.000): Thẻ kỹ năng trực tiếp từ listing/details
      2. title_keyword (Độ tin cậy 0.950): Từ khóa công nghệ xuất hiện trong chức danh
      3. requirement_rule (Độ tin cậy 0.900): Quy tắc regex trong mục yêu cầu ứng viên
      4. description_rule (Độ tin cậy 0.800): Quy tắc regex trong mục mô tả công việc
    """
    df_merged = bronze_data["df_merged"]
    pats = get_skill_patterns()

    matchers = []
    for idx, s in enumerate(SKILLS_TAXONOMY):
        skill_id = idx + 1
        name = s["name"]
        pat = pats.get(name, r"\b" + re.escape(name.lower()) + r"\b")
        matchers.append({
            "skill_id": skill_id,
            "skill_name": name,
            "regex": re.compile(pat, re.IGNORECASE)
        })

    print(f"-> [Transformer: job_skills] Trích xuất kỹ năng từ {len(df_merged):,} tin việc làm với 76 bộ matcher...")
    job_skills_dict = {}

    for idx, row in df_merged.iterrows():
        job_id = int(row["job_id"])

        # 1. Thu thập các thẻ kỹ năng có sẵn từ tin tuyển dụng
        raw_tags = row.get("skills_raw") or []
        if isinstance(raw_tags, str):
            raw_tags = [x.strip() for x in raw_tags.split(",") if x.strip()]
        elif not isinstance(raw_tags, list):
            raw_tags = []

        req_skills_raw = row.get("required_skills_raw") or []
        if isinstance(req_skills_raw, str):
            req_skills_raw = [x.strip() for x in req_skills_raw.split(",") if x.strip()]
        elif not isinstance(req_skills_raw, list):
            req_skills_raw = []

        pref_skills_raw = row.get("preferred_skills_raw") or []
        if isinstance(pref_skills_raw, str):
            pref_skills_raw = [x.strip() for x in pref_skills_raw.split(",") if x.strip()]
        elif not isinstance(pref_skills_raw, list):
            pref_skills_raw = []

        all_req_tags = " ".join(raw_tags + req_skills_raw)
        all_pref_tags = " ".join(pref_skills_raw)

        title_raw = str(row.get("title_raw", "") or "")
        req_raw = str(row.get("requirements_raw", "") or "")
        resp_raw = str(row.get("responsibilities_raw", "") or "")

        for sm in matchers:
            s_id = sm["skill_id"]
            reg = sm["regex"]
            key = (job_id, s_id)

            # Tầng 1: Thẻ tag trực tiếp (Độ tin cậy 1.000)
            m_tag = reg.search(all_req_tags)
            if m_tag:
                ev = f"Tag: {all_req_tags[max(0, m_tag.start()-10):min(len(all_req_tags), m_tag.end()+25)].strip()}"
                job_skills_dict[key] = {
                    "job_id": job_id,
                    "skill_id": s_id,
                    "skill_type": "required",
                    "confidence": 1.000,
                    "extraction_method": "tag_direct",
                    "evidence_text": ev[:255]
                }
                continue

            m_ptag = reg.search(all_pref_tags)
            if m_ptag:
                ev = f"Tag ưu tiên: {all_pref_tags[max(0, m_ptag.start()-10):min(len(all_pref_tags), m_ptag.end()+25)].strip()}"
                job_skills_dict[key] = {
                    "job_id": job_id,
                    "skill_id": s_id,
                    "skill_type": "preferred",
                    "confidence": 1.000,
                    "extraction_method": "tag_direct",
                    "evidence_text": ev[:255]
                }
                continue

            # Tầng 2: Từ khóa trong chức danh (Độ tin cậy 0.950)
            m_title = reg.search(title_raw)
            if m_title:
                ev = f"Tiêu đề: {title_raw[:120].strip()}"
                job_skills_dict[key] = {
                    "job_id": job_id,
                    "skill_id": s_id,
                    "skill_type": "required",
                    "confidence": 0.950,
                    "extraction_method": "title_keyword",
                    "evidence_text": ev[:255]
                }
                continue

            # Tầng 3: Quy tắc regex trong yêu cầu (Độ tin cậy 0.900)
            m_req = reg.search(req_raw)
            if m_req:
                start_p = max(0, m_req.start() - 30)
                end_p = min(len(req_raw), m_req.end() + 60)
                snippet = req_raw[start_p:end_p].replace("\n", " ").strip()
                is_pref = check_is_preferred(snippet)
                ev = f"Yêu cầu: ...{snippet}..."
                job_skills_dict[key] = {
                    "job_id": job_id,
                    "skill_id": s_id,
                    "skill_type": "preferred" if is_pref else "required",
                    "confidence": 0.900,
                    "extraction_method": "requirement_rule",
                    "evidence_text": ev[:255]
                }
                continue

            # Tầng 4: Quy tắc regex trong mô tả / trách nhiệm (Độ tin cậy 0.800)
            m_resp = reg.search(resp_raw)
            if m_resp:
                start_p = max(0, m_resp.start() - 30)
                end_p = min(len(resp_raw), m_resp.end() + 60)
                snippet = resp_raw[start_p:end_p].replace("\n", " ").strip()
                ev = f"Mô tả: ...{snippet}..."
                job_skills_dict[key] = {
                    "job_id": job_id,
                    "skill_id": s_id,
                    "skill_type": "required",
                    "confidence": 0.800,
                    "extraction_method": "description_rule",
                    "evidence_text": ev[:255]
                }
                continue

    job_skills_records = list(job_skills_dict.values())
    unique_jobs = len(set(r["job_id"] for r in job_skills_records))
    unique_skills = len(set(r["skill_id"] for r in job_skills_records))
    req_count = sum(1 for r in job_skills_records if r["skill_type"] == "required")
    pref_count = sum(1 for r in job_skills_records if r["skill_type"] == "preferred")

    print(f"   [Transformer: job_skills] Đã trích xuất thành công: {len(job_skills_records):,} cặp liên kết (job_id, skill_id).")
    print(f"   [Transformer: job_skills] Số lượng việc làm có kỹ năng: {unique_jobs:,} / {len(df_merged):,} ({unique_jobs/len(df_merged)*100:.1f}%).")
    print(f"   [Transformer: job_skills] Phân loại kỹ năng: {req_count:,} bắt buộc (required), {pref_count:,} ưu tiên (preferred).")
    print(f"   [Transformer: job_skills] Độ bao phủ danh mục: {unique_skills}/76 kỹ năng ({unique_skills/76*100:.1f}%).")

    return job_skills_records

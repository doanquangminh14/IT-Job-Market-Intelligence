import re
from typing import List, Optional

# Bảng quy chuẩn hiển thị cho các công nghệ IT & Data phổ biến (Canonical Mapping)
CANONICAL_SKILL_MAP = {
    # 1. Ngôn ngữ lập trình (Programming Languages)
    'python': 'Python', 'py': 'Python', 'python3': 'Python',
    'java': 'Java', 'java core': 'Java',
    'javascript': 'JavaScript', 'js': 'JavaScript',
    'typescript': 'TypeScript', 'ts': 'TypeScript',
    'c++': 'C++', 'cpp': 'C++',
    'c#': 'C#', 'csharp': 'C#',
    'php': 'PHP',
    'golang': 'Golang', 'go': 'Golang',
    'ruby': 'Ruby',
    'rust': 'Rust',
    'scala': 'Scala',
    'kotlin': 'Kotlin',
    'swift': 'Swift',
    'dart': 'Dart',
    'r': 'R',
    'bash': 'Bash', 'shell': 'Shell',
    'powershell': 'PowerShell',

    # 2. Phân tích dữ liệu & BI (Data Analytics & BI)
    'sql': 'SQL', 't-sql': 'T-SQL', 'pl/sql': 'PL/SQL',
    'power bi': 'Power BI', 'powerbi': 'Power BI', 'pbi': 'Power BI',
    'tableau': 'Tableau',
    'excel': 'Excel', 'vba': 'VBA', 'macro': 'VBA',
    'dax': 'DAX',
    'power query': 'Power Query', 'powerquery': 'Power Query',
    'looker': 'Looker', 'looker studio': 'Looker',
    'metabase': 'Metabase',
    'google data studio': 'Looker',
    'qlik': 'Qlik', 'qliksense': 'Qlik', 'qlikview': 'Qlik',
    'ssis': 'SSIS', 'ssrs': 'SSRS', 'ssas': 'SSAS',
    'google analytics': 'Google Analytics', 'ga4': 'Google Analytics',
    'a/b testing': 'A/B Testing', 'ab testing': 'A/B Testing',

    # 3. Kỹ thuật dữ liệu & Big Data (Data Engineering & Big Data)
    'etl': 'ETL', 'elt': 'ELT',
    'data warehouse': 'Data Warehouse', 'dwh': 'Data Warehouse',
    'data lake': 'Data Lake',
    'data modeling': 'Data Modeling',
    'data pipeline': 'Data Pipeline',
    'bigquery': 'BigQuery',
    'snowflake': 'Snowflake',
    'spark': 'Apache Spark', 'pyspark': 'PySpark', 'apache spark': 'Apache Spark',
    'hadoop': 'Hadoop', 'hive': 'Hive',
    'airflow': 'Apache Airflow', 'apache airflow': 'Apache Airflow',
    'dbt': 'dbt',
    'kafka': 'Apache Kafka', 'apache kafka': 'Apache Kafka',
    'spark streaming': 'Apache Spark',

    # 4. Khoa học dữ liệu & Trí tuệ nhân tạo (Data Science & AI/ML)
    'machine learning': 'Machine Learning', 'ml': 'Machine Learning',
    'deep learning': 'Deep Learning', 'dl': 'Deep Learning',
    'nlp': 'NLP', 'natural language processing': 'NLP',
    'computer vision': 'Computer Vision', 'cv': 'Computer Vision',
    'pandas': 'Pandas',
    'numpy': 'NumPy',
    'scikit-learn': 'Scikit-Learn', 'sklearn': 'Scikit-Learn',
    'tensorflow': 'TensorFlow',
    'pytorch': 'PyTorch',
    'keras': 'Keras',
    'generative ai': 'Generative AI', 'genai': 'Generative AI',
    'llm': 'LLM',
    'statistics': 'Statistics',

    # 5. Backend Frameworks & Web
    'spring boot': 'Spring Boot', 'springboot': 'Spring Boot', 'spring': 'Spring Boot',
    'django': 'Django',
    'fastapi': 'FastAPI',
    'flask': 'Flask',
    'node.js': 'Node.js', 'nodejs': 'Node.js', 'node': 'Node.js',
    'express.js': 'Express.js', 'expressjs': 'Express.js', 'express': 'Express.js',
    'nestjs': 'NestJS', 'nest.js': 'NestJS',
    '.net': '.NET', 'dotnet': '.NET', '.net core': '.NET', 'asp.net': '.NET',
    'laravel': 'Laravel',
    'ruby on rails': 'Ruby on Rails', 'rails': 'Ruby on Rails',
    'gin': 'Gin',
    'graphql': 'GraphQL',
    'rest api': 'REST API', 'restful': 'REST API', 'restful api': 'REST API',
    'grpc': 'gRPC',
    'microservices': 'Microservices', 'microservice': 'Microservices',

    # 6. Frontend & Mobile Frameworks
    'react': 'React', 'reactjs': 'React', 'react.js': 'React',
    'react native': 'React Native', 'reactnative': 'React Native',
    'vue': 'Vue', 'vuejs': 'Vue', 'vue.js': 'Vue',
    'angular': 'Angular', 'angularjs': 'Angular',
    'next.js': 'Next.js', 'nextjs': 'Next.js',
    'nuxt.js': 'Nuxt.js', 'nuxtjs': 'Nuxt.js',
    'svelte': 'Svelte',
    'flutter': 'Flutter',
    'android': 'Android',
    'ios': 'iOS',
    'html': 'HTML/CSS', 'html5': 'HTML/CSS',
    'css': 'HTML/CSS', 'css3': 'HTML/CSS',
    'tailwind': 'TailwindCSS', 'tailwindcss': 'TailwindCSS',
    'bootstrap': 'Bootstrap',
    'redux': 'Redux',

    # 7. Cơ sở dữ liệu (Databases)
    'postgresql': 'PostgreSQL', 'postgres': 'PostgreSQL', 'psql': 'PostgreSQL',
    'mysql': 'MySQL',
    'sql server': 'SQL Server', 'mssql': 'SQL Server',
    'oracle': 'Oracle Database',
    'mongodb': 'MongoDB', 'mongo': 'MongoDB',
    'redis': 'Redis',
    'elasticsearch': 'Elasticsearch', 'elastic': 'Elasticsearch',
    'cassandra': 'Cassandra',
    'dynamodb': 'DynamoDB',
    'sqlite': 'SQLite',
    'mariadb': 'MariaDB',
    'firebase': 'Firebase',
    'neo4j': 'Neo4j',

    # 8. Cloud & DevOps
    'aws': 'AWS', 'amazon web services': 'AWS',
    'azure': 'Azure', 'microsoft azure': 'Azure',
    'gcp': 'GCP', 'google cloud': 'GCP',
    'docker': 'Docker',
    'kubernetes': 'Kubernetes', 'k8s': 'Kubernetes',
    'ci/cd': 'CI/CD', 'cicd': 'CI/CD',
    'git': 'Git', 'github': 'Git', 'gitlab': 'Git',
    'linux': 'Linux',
    'terraform': 'Terraform',
    'ansible': 'Ansible',
    'jenkins': 'Jenkins',
    'nginx': 'Nginx',
    'prometheus': 'Prometheus',
    'grafana': 'Grafana',
    'rabbitmq': 'RabbitMQ',

    # 9. Kiểm thử phần mềm (QA & Testing)
    'manual testing': 'Manual Testing', 'manual test': 'Manual Testing',
    'automation testing': 'Automation Testing', 'automation test': 'Automation Testing',
    'selenium': 'Selenium',
    'cypress': 'Cypress',
    'playwright': 'Playwright',
    'postman': 'Postman',
    'jmeter': 'JMeter',
    'unit test': 'Unit Testing', 'unit testing': 'Unit Testing',
    'appium': 'Appium',

    # 10. Quản lý, Thiết kế & Phương pháp luận (Tools & Methodologies)
    'jira': 'Jira',
    'confluence': 'Confluence',
    'figma': 'Figma',
    'photoshop': 'Photoshop',
    'agile': 'Agile',
    'scrum': 'Scrum',
    'oop': 'OOP',
    'system design': 'System Design',
    'an ninh mạng': 'An Ninh Mạng', 'cybersecurity': 'An Ninh Mạng'
}

# Danh sách từ khóa rác, phúc lợi, nhân thân, ngành nghề cần loại trừ triệt để
EXCLUDE_PATTERNS = [
    # 1. Phúc lợi, phụ cấp, thiết bị cá nhân
    r'xăng\s*xe', r'xăng', r'xe\s*máy', r'tai\s*nghe', r'ăn\s*trưa', r'cơm\s*trưa', r'tiền\s*ăn',
    r'gửi\s*xe', r'vé\s*xe', r'bãi\s*xe', r'đồng\s*phục', r'điện\s*thoại', r'laptop', r'máy\s*tính',
    r'thiết\s*bị', r'cấp\s*phát', r'công\s*cụ\s*làm\s*việc', r'bảo\s*hiểm', r'bhxh', r'bhyt', r'bhtn',
    r'khám\s*sức\s*khỏe', r'khám\s*định\s*kỳ', r'thưởng', r'tháng\s*13', r'lương\s*tháng', r'bonus',
    r'hoa\s*hồng', r'du\s*lịch', r'nghỉ\s*mát', r'nghỉ\s*phép', r'phép\s*năm', r'team\s*building',
    r'teambuilding', r'sinh\s*nhật', r'quà\s*tặng', r'hiếu\s*hỉ', r'thể\s*thao', r'gym', r'yoga',
    r'chăm\s*sóc', r'đãi\s*ngộ', r'phụ\s*cấp', r'hỗ\s*trợ',

    # 2. Ngành nghề / Lĩnh vực doanh nghiệp (Domain / Industry)
    r'thương\s*mại\s*điện\s*tử', r'e-?commerce', r'bán\s*lẻ', r'ngân\s*hàng', r'tài\s*chính',
    r'chứng\s*khoán', r'bất\s*động\s*sản', r'giáo\s*dục', r'y\s*tế', r'fmcg', r'logistics',
    r'xuất\s*nhập\s*khẩu', r'sản\s*xuất', r'nông\s*nghiệp', r'du\s*lịch\s*-\s*khách\s*sạn', r'f&b',
    r'xây\s*dựng', r'nội\s*thất', r'thực\s*phẩm', r'dược\s*phẩm', r'viễn\s*thông', r'vận\s*tải',

    # 3. Kênh bán hàng, chức năng thương mại không thuộc IT
    r'b2b', r'b2c', r'telesales', r'direct\s*sales', r'online\s*sales', r'bán\s*hàng',
    r'tư\s*vấn', r'kinh\s*doanh', r'chăm\s*sóc\s*khách\s*hàng', r'cskh', r'sales?',
    r'marketing', r'quảng\s*cáo', r'digital\s*marketing', r'seo', r'content', r'kinh\s*doanh\s*phần\s*mềm',

    # 4. Chức danh, cấp bậc (Job Titles, Seniority)
    r'data\s*analyst', r'business\s*analyst', r'developer', r'tester', r'engineer',
    r'product\s*owner', r'product\s*manager', r'nhân\s*viên', r'chuyên\s*viên', r'trưởng\s*nhóm',
    r'quản\s*lý', r'thực\s*tập', r'fresher', r'intern', r'junior', r'middle', r'senior',
    r'leader?', r'head', r'giám\s*đốc', r'cán\s*bộ', r'trợ\s*lý', r'thư\s*ký',

    # 5. Phân loại chung của sàn và tiêu chí nhân thân
    r'it\s*-\s*phần\s*mềm', r'công\s*nghệ\s*thông\s*tin\s*khác', r'chuyên\s*môn', r'toàn\s*thời\s*gian',
    r'bán\s*thời\s*gian', r'full\s*time', r'part\s*time', r'onsite', r'remote', r'hybrid',
    r'cao\s*đẳng', r'đại\s*học', r'trung\s*cấp', r'bằng\s*cấp', r'chứng\s*chỉ', r'kinh\s*nghiệm',
    r'trở\s*lên', r'yêu\s*cầu', r'kỹ\s*năng', r'tiêu\s*chuẩn', r'trách\s*nhiệm', r'nhiệm\s*vụ',
    r'tuổi\s*\d+', r'nam', r'nữ', r'giới\s*tính', r'xem\s*tất\s*cả', r'đọc\s*hiểu', r'giao\s*tiếp',
    r'mỹ\s*thuật', r'nghệ\s*thuật', r'kiến\s*trúc'
]


def normalize_skill_name(skill_str: str) -> Optional[str]:
    """
    Chuẩn hóa tên kỹ năng về dạng chuẩn (Canonical Form).
    Chỉ trả về tên chuẩn nếu là kỹ năng công nghệ thực sự.
    """
    if not skill_str:
        return None
    s = skill_str.strip()
    key = s.lower()
    
    # Kiểm tra từ rác
    if any(re.search(pat, key) for pat in EXCLUDE_PATTERNS):
        return None
        
    # Trực tiếp trong từ điển
    if key in CANONICAL_SKILL_MAP:
        return CANONICAL_SKILL_MAP[key]
        
    # Chấp nhận các thuật ngữ kỹ thuật ASCII ngắn (tiếng Anh) hợp lệ
    if re.match(r'^[a-zA-Z0-9#\+\.\/\-_ ]{2,25}$', s) and not any(ord(c) > 127 for c in s):
        # Tránh các từ tiếng Anh quá chung chung
        if key not in {'other', 'another', 'etc', 'plus', 'good', 'well', 'basic', 'skill', 'tools'}:
            return s.title() if len(s) <= 15 else s
            
    return None


# ==============================================================================
# KỸ NĂNG CÔNG NGHỆ vs THẺ NGÀNH (đồng bộ với notebook 02, Bước 4)
# ==============================================================================
# required_skills_raw của TopCV/VietnamWorks trộn lẫn kỹ năng công nghệ, thẻ ngành/chức danh/ngoại ngữ và rác
# (phúc lợi, kinh nghiệm...). Kỹ năng ➔ `required_skills`, thẻ ➔ `job_tags`, rác ➔ loại bỏ.

# 2. Khái niệm công nghệ hay gặp trong thẻ của sàn nhưng chưa có trong từ điển trên
TECH_EXTRA = {
    'data analysis': 'Data Analysis', 'data analytics': 'Data Analysis', 'phân tích dữ liệu': 'Data Analysis',
    'data science': 'Data Science', 'big data': 'Big Data', 'business intelligence': 'Business Intelligence',
    'data management': 'Data Management', 'data governance': 'Data Governance',
    'cloud': 'Cloud', 'điện toán đám mây (cloud)': 'Cloud', 'devops': 'DevOps', 'api': 'API', 'api testing': 'API Testing',
    'erp': 'ERP', 'sap': 'SAP', 'scada': 'SCADA', 'vmware': 'VMware', 'hosting': 'Hosting', 'server': 'Server',
    'software testing': 'Software Testing', 'kiểm thử phần mềm': 'Software Testing', 'qa': 'QA',
    'information security': 'An Ninh Mạng', 'it security': 'An Ninh Mạng', 'an toàn thông tin': 'An Ninh Mạng',
    'network security': 'Network Security',
    'lập trình nhúng': 'Embedded', 'embedded': 'Embedded', 'network': 'Networking', 'quản trị mạng': 'Networking',
    'system administration': 'System Administration', 'quản trị hệ thống': 'System Administration',
    'agile scrum': 'Agile', 'ux design': 'UX Design', 'ui': 'UI Design',
    'ms sql': 'SQL Server', 'python programming': 'Python', 'java spring boot': 'Spring Boot',
    'ci': 'CI/CD', 'cd': 'CI/CD', 'cd methodologies': 'CI/CD', 'ai': 'AI', 'blockchain': 'Blockchain',
}
TECH_LOOKUP = {**CANONICAL_SKILL_MAP, **TECH_EXTRA}

# 3. Khóa quá mơ hồ khi quét VĂN BẢN TỰ DO (vd 'go' trong "go to market", 'cv' trong "gửi CV", 'ml' viết tắt)
#    ➔ chỉ chấp nhận chúng khi xuất hiện như một THẺ rõ ràng, không quét từ mô tả.
AMBIGUOUS_FREE_TEXT_KEYS = {'cv', 'go', 'r', 'ml', 'dl', 'py', 'ts', 'js', 'macro', 'gin', 'spring', 'express',
                            'node', 'shell', 'elastic', 'ai', 'ui', 'ci', 'cd', 'api', 'qa', 'server', 'cloud', 'network', 'sap'}

# 4. Mẫu nhận diện thẻ RÁC (phúc lợi, kinh nghiệm, học vấn, nhân thân...)
JUNK_PATTERN = re.compile(
    r'bảo hiểm|thưởng|bonus|du lịch|team\s*building|khám sức khỏe|phụ cấp|xăng|tai nghe|cước|điện thoại|phương tiện|'
    r'giờ hành chính|giọng|phát âm|diễn đạt|kinh nghiệm|trở lên|đại học|cao đẳng|trung cấp|tuổi|xem tất cả|'
    r'toàn thời gian|bán thời gian|thực tập|signing', re.IGNORECASE)

# 5. Regex quét kỹ năng trong văn bản. Dùng lookaround thay cho \b để nhận đúng C++, C#, .NET, CI/CD
TECH_PATTERNS = [
    (re.compile(r'(?<![\w+#.])' + re.escape(key) + r'(?![\w+#])'), canonical)
    for key, canonical in TECH_LOOKUP.items() if key not in AMBIGUOUS_FREE_TEXT_KEYS
]


def classify_tag(tag):
    """Phân loại một thẻ thô: ('skill', tên chuẩn) | ('tag', tên giữ nguyên) | ('junk', None)."""
    key = re.sub(r'\s+', ' ', tag).strip().lower()
    if key in TECH_LOOKUP:
        return 'skill', TECH_LOOKUP[key]
    if JUNK_PATTERN.search(key):
        return 'junk', None
    return 'tag', re.sub(r'\s+', ' ', tag).strip()


def extract_skills_and_tags(row):
    skills, tags, seen_s, seen_t = [], [], set(), set()

    # (a) Tách chuỗi thẻ thô. KHÔNG tách theo dấu "/" để giữ nguyên CI/CD, A/B Testing
    for part in re.split(r'[,;|•\n]', str(row.get('required_skills_raw', ''))):
        item = part.strip()
        if len(item) <= 1 or len(item) > 60:
            continue
        kind, name = classify_tag(item)
        if kind == 'skill' and name.lower() not in seen_s:
            seen_s.add(name.lower()); skills.append(name)
        elif kind == 'tag' and name.lower() not in seen_t:
            seen_t.add(name.lower()); tags.append(name)

    # (b) Bổ sung kỹ năng công nghệ quét từ mô tả JD
    desc = str(row.get('description_clean', '')).lower()
    for pattern, canonical in TECH_PATTERNS:
        if canonical.lower() not in seen_s and pattern.search(desc):
            seen_s.add(canonical.lower()); skills.append(canonical)
    return skills, tags


def extract_skills_from_text(text: str) -> List[str]:
    """Bóc tách kỹ năng công nghệ chuẩn hóa từ văn bản tự do (mô tả JD / nội dung CV)."""
    if not text:
        return []
    text_lower = str(text).lower()
    found, seen = [], set()
    for pattern, canonical in TECH_PATTERNS:
        if canonical.lower() not in seen and pattern.search(text_lower):
            seen.add(canonical.lower())
            found.append(canonical)
    return found


def normalize_user_skills(skills) -> List[str]:
    """Chuẩn hóa kỹ năng người dùng nhập tay: 'reactjs' ➔ 'React', 'k8s' ➔ 'Kubernetes'."""
    return [TECH_LOOKUP.get(str(s).strip().lower(), str(s).strip()) for s in (skills or []) if str(s).strip()]

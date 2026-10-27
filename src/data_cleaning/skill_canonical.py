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


def extract_skills_from_text(text: str) -> List[str]:
    """
    Tự động quét và trích xuất danh sách kỹ năng chuẩn hóa từ văn bản bất kỳ (mô tả JD hoặc nội dung CV).
    """
    if not text:
        return []
    text_lower = str(text).lower()
    detected = []
    seen = set()
    
    for key, val in CANONICAL_SKILL_MAP.items():
        # Kiểm tra biên từ để tránh nhận nhầm từ con
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, text_lower):
            if val.lower() not in seen:
                seen.add(val.lower())
                detected.append(val)
                
    return detected

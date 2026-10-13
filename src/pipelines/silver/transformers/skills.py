from datetime import datetime

# Danh mục 76 kỹ năng IT chuẩn hóa phân chia theo 10 nhóm chuyên môn
SKILLS_TAXONOMY = [
    # 1. Programming Languages
    {"name": "Python", "canonical": "python", "cat": "Programming Language", "parent": None, "desc": "Ngôn ngữ lập trình đa dụng, AI/Data, Backend"},
    {"name": "Java", "canonical": "java", "cat": "Programming Language", "parent": None, "desc": "Ngôn ngữ lập trình hướng đối tượng doanh nghiệp"},
    {"name": "JavaScript", "canonical": "javascript", "cat": "Programming Language", "parent": None, "desc": "Ngôn ngữ lập trình web phổ biến nhất"},
    {"name": "TypeScript", "canonical": "typescript", "cat": "Programming Language", "parent": "JavaScript", "desc": "Phiên bản typed của JavaScript"},
    {"name": "C++", "canonical": "cpp", "cat": "Programming Language", "parent": None, "desc": "Ngôn ngữ lập trình hệ thống hiệu năng cao"},
    {"name": "C#", "canonical": "csharp", "cat": "Programming Language", "parent": None, "desc": "Ngôn ngữ lập trình hệ sinh thái .NET"},
    {"name": "PHP", "canonical": "php", "cat": "Programming Language", "parent": None, "desc": "Ngôn ngữ lập trình backend web truyền thống"},
    {"name": "Golang", "canonical": "golang", "cat": "Programming Language", "parent": None, "desc": "Ngôn ngữ biên dịch hiệu năng cao của Google"},
    {"name": "Ruby", "canonical": "ruby", "cat": "Programming Language", "parent": None, "desc": "Ngôn ngữ lập trình hướng đối tượng linh hoạt"},
    {"name": "Kotlin", "canonical": "kotlin", "cat": "Programming Language", "parent": "Java", "desc": "Ngôn ngữ lập trình hiện đại cho Android và JVM"},
    {"name": "Swift", "canonical": "swift", "cat": "Programming Language", "parent": None, "desc": "Ngôn ngữ lập trình hệ sinh thái Apple iOS/macOS"},
    {"name": "Rust", "canonical": "rust", "cat": "Programming Language", "parent": None, "desc": "Ngôn ngữ hệ thống an toàn bộ nhớ"},
    {"name": "Dart", "canonical": "dart", "cat": "Programming Language", "parent": None, "desc": "Ngôn ngữ phát triển ứng dụng Flutter"},
    {"name": "Scala", "canonical": "scala", "cat": "Programming Language", "parent": "Java", "desc": "Ngôn ngữ kết hợp OOP và FP cho Big Data"},

    # 2. Frontend Development
    {"name": "HTML/CSS", "canonical": "html_css", "cat": "Frontend Development", "parent": None, "desc": "Nền tảng xây dựng giao diện web"},
    {"name": "React", "canonical": "react", "cat": "Frontend Development", "parent": "JavaScript", "desc": "Thư viện frontend phổ biến nhất của Meta"},
    {"name": "Vue.js", "canonical": "vuejs", "cat": "Frontend Development", "parent": "JavaScript", "desc": "Progressive framework frontend"},
    {"name": "Angular", "canonical": "angular", "cat": "Frontend Development", "parent": "TypeScript", "desc": "Framework frontend toàn diện của Google"},
    {"name": "Next.js", "canonical": "nextjs", "cat": "Frontend Development", "parent": "React", "desc": "React framework hỗ trợ SSR và full-stack"},
    {"name": "Tailwind CSS", "canonical": "tailwindcss", "cat": "Frontend Development", "parent": "HTML/CSS", "desc": "Utility-first CSS framework"},
    {"name": "Nuxt.js", "canonical": "nuxtjs", "cat": "Frontend Development", "parent": "Vue.js", "desc": "Vue framework hỗ trợ SSR"},
    {"name": "Redux", "canonical": "redux", "cat": "Frontend Development", "parent": "React", "desc": "Thư viện quản lý state"},

    # 3. Backend Development
    {"name": "Node.js", "canonical": "nodejs", "cat": "Backend Development", "parent": "JavaScript", "desc": "Runtime JavaScript phía server"},
    {"name": "Spring Boot", "canonical": "spring_boot", "cat": "Backend Development", "parent": "Java", "desc": "Framework backend Java phổ biến nhất"},
    {"name": ".NET", "canonical": "dotnet", "cat": "Backend Development", "parent": "C#", "desc": "Nền tảng phát triển backend của Microsoft"},
    {"name": "Django", "canonical": "django", "cat": "Backend Development", "parent": "Python", "desc": "Full-stack web framework cho Python"},
    {"name": "FastAPI", "canonical": "fastapi", "cat": "Backend Development", "parent": "Python", "desc": "High-performance API framework cho Python"},
    {"name": "Flask", "canonical": "flask", "cat": "Backend Development", "parent": "Python", "desc": "Micro-framework web cho Python"},
    {"name": "Laravel", "canonical": "laravel", "cat": "Backend Development", "parent": "PHP", "desc": "Framework PHP phổ biến nhất"},
    {"name": "Express.js", "canonical": "expressjs", "cat": "Backend Development", "parent": "Node.js", "desc": "Web framework tối giản cho Node.js"},
    {"name": "NestJS", "canonical": "nestjs", "cat": "Backend Development", "parent": "Node.js", "desc": "Framework backend TypeScript hướng đối tượng"},
    {"name": "Ruby on Rails", "canonical": "rails", "cat": "Backend Development", "parent": "Ruby", "desc": "Web application framework cho Ruby"},

    # 4. Database & Storage
    {"name": "SQL", "canonical": "sql", "cat": "Database & Storage", "parent": None, "desc": "Ngôn ngữ truy vấn cơ sở dữ liệu quan hệ chuẩn"},
    {"name": "PostgreSQL", "canonical": "postgresql", "cat": "Database & Storage", "parent": "SQL", "desc": "Hệ quản trị CSDL quan hệ mã nguồn mở mạnh mẽ"},
    {"name": "MySQL", "canonical": "mysql", "cat": "Database & Storage", "parent": "SQL", "desc": "Hệ quản trị CSDL quan hệ phổ biến"},
    {"name": "MongoDB", "canonical": "mongodb", "cat": "Database & Storage", "parent": None, "desc": "Cơ sở dữ liệu NoSQL hướng tài liệu phổ biến nhất"},
    {"name": "Redis", "canonical": "redis", "cat": "Database & Storage", "parent": None, "desc": "In-memory data store phục vụ caching"},
    {"name": "Oracle", "canonical": "oracle", "cat": "Database & Storage", "parent": "SQL", "desc": "Hệ quản trị CSDL doanh nghiệp lớn của Oracle"},
    {"name": "SQL Server", "canonical": "sql_server", "cat": "Database & Storage", "parent": "SQL", "desc": "Hệ quản trị CSDL của Microsoft"},
    {"name": "Elasticsearch", "canonical": "elasticsearch", "cat": "Database & Storage", "parent": None, "desc": "Search & analytics engine phân tán"},

    # 5. Cloud & DevOps
    {"name": "Docker", "canonical": "docker", "cat": "Cloud & DevOps", "parent": None, "desc": "Nền tảng container hóa ứng dụng"},
    {"name": "Kubernetes", "canonical": "kubernetes", "cat": "Cloud & DevOps", "parent": "Docker", "desc": "Nền tảng điều phối container (K8s)"},
    {"name": "AWS", "canonical": "aws", "cat": "Cloud & DevOps", "parent": None, "desc": "Dịch vụ điện toán đám mây của Amazon"},
    {"name": "Azure", "canonical": "azure", "cat": "Cloud & DevOps", "parent": None, "desc": "Dịch vụ điện toán đám mây của Microsoft"},
    {"name": "GCP", "canonical": "gcp", "cat": "Cloud & DevOps", "parent": None, "desc": "Google Cloud Platform"},
    {"name": "CI/CD", "canonical": "ci_cd", "cat": "Cloud & DevOps", "parent": None, "desc": "Quy trình tích hợp và triển khai tự động"},
    {"name": "Linux", "canonical": "linux", "cat": "Cloud & DevOps", "parent": None, "desc": "Hệ điều hành máy chủ tiêu chuẩn"},
    {"name": "Terraform", "canonical": "terraform", "cat": "Cloud & DevOps", "parent": None, "desc": "Infrastructure as Code (IaC) tool"},
    {"name": "Ansible", "canonical": "ansible", "cat": "Cloud & DevOps", "parent": None, "desc": "Công cụ cấu hình và tự động hóa hệ thống"},

    # 6. AI & Data Science
    {"name": "Machine Learning", "canonical": "machine_learning", "cat": "AI & Data Science", "parent": None, "desc": "Học máy và mô hình dự báo"},
    {"name": "Deep Learning", "canonical": "deep_learning", "cat": "AI & Data Science", "parent": "Machine Learning", "desc": "Mạng nơ-ron học sâu"},
    {"name": "PyTorch", "canonical": "pytorch", "cat": "AI & Data Science", "parent": "Python", "desc": "Thư viện Deep Learning của Meta"},
    {"name": "TensorFlow", "canonical": "tensorflow", "cat": "AI & Data Science", "parent": "Python", "desc": "Nền tảng Deep Learning của Google"},
    {"name": "NLP", "canonical": "nlp", "cat": "AI & Data Science", "parent": "Machine Learning", "desc": "Xử lý ngôn ngữ tự nhiên"},
    {"name": "Computer Vision", "canonical": "computer_vision", "cat": "AI & Data Science", "parent": "Machine Learning", "desc": "Thị giác máy tính và xử lý ảnh"},
    {"name": "LLM", "canonical": "llm", "cat": "AI & Data Science", "parent": "NLP", "desc": "Mô hình ngôn ngữ lớn và Generative AI"},
    {"name": "Pandas", "canonical": "pandas", "cat": "AI & Data Science", "parent": "Python", "desc": "Thư viện phân tích và xử lý bảng dữ liệu"},
    {"name": "NumPy", "canonical": "numpy", "cat": "AI & Data Science", "parent": "Python", "desc": "Thư viện tính toán ma trận và số học"},
    {"name": "Spark", "canonical": "spark", "cat": "AI & Data Science", "parent": None, "desc": "Engine xử lý dữ liệu lớn phân tán"},
    {"name": "Kafka", "canonical": "kafka", "cat": "AI & Data Science", "parent": None, "desc": "Nền tảng streaming dữ liệu phân tán"},

    # 7. Mobile Development
    {"name": "React Native", "canonical": "react_native", "cat": "Mobile Development", "parent": "React", "desc": "Cross-platform mobile framework bằng React"},
    {"name": "Flutter", "canonical": "flutter", "cat": "Mobile Development", "parent": "Dart", "desc": "Cross-platform mobile framework của Google"},
    {"name": "Android", "canonical": "android", "cat": "Mobile Development", "parent": "Kotlin", "desc": "Phát triển ứng dụng Android native"},
    {"name": "iOS", "canonical": "ios", "cat": "Mobile Development", "parent": "Swift", "desc": "Phát triển ứng dụng iOS native"},

    # 8. Testing & QA
    {"name": "Manual Testing", "canonical": "manual_testing", "cat": "Testing & QA", "parent": None, "desc": "Kiểm thử thủ công chức năng và giao diện"},
    {"name": "Automation Testing", "canonical": "automation_testing", "cat": "Testing & QA", "parent": None, "desc": "Kiểm thử tự động hóa"},
    {"name": "Selenium", "canonical": "selenium", "cat": "Testing & QA", "parent": "Automation Testing", "desc": "Framework tự động hóa trình duyệt web"},
    {"name": "Postman", "canonical": "postman", "cat": "Testing & QA", "parent": None, "desc": "Công cụ kiểm thử và phát triển API"},
    {"name": "JMeter", "canonical": "jmeter", "cat": "Testing & QA", "parent": None, "desc": "Công cụ kiểm thử tải và hiệu năng"},
    {"name": "Cypress", "canonical": "cypress", "cat": "Testing & QA", "parent": "Automation Testing", "desc": "Front-end testing tool hiện đại"},

    # 9. Security & Architecture
    {"name": "Microservices", "canonical": "microservices", "cat": "Security & Architecture", "parent": None, "desc": "Kiến trúc dịch vụ vi mô phân tán"},
    {"name": "Security", "canonical": "security", "cat": "Security & Architecture", "parent": None, "desc": "Bảo mật thông tin và an ninh mạng"},
    {"name": "OAuth", "canonical": "oauth", "cat": "Security & Architecture", "parent": "Security", "desc": "Chuẩn xác thực và ủy quyền truy cập"},

    # 10. Methodology & Tools
    {"name": "Git", "canonical": "git", "cat": "Methodology & Tools", "parent": None, "desc": "Hệ thống quản lý phiên bản mã nguồn phân tán"},
    {"name": "Agile/Scrum", "canonical": "agile_scrum", "cat": "Methodology & Tools", "parent": None, "desc": "Phương pháp luận phát triển phần mềm linh hoạt"},
    {"name": "Jira", "canonical": "jira", "cat": "Methodology & Tools", "parent": "Agile/Scrum", "desc": "Hệ thống quản lý tác vụ và dự án phần mềm"}
]

def transform_skills():
    """
    Tạo danh sách 76 kỹ năng chuẩn hóa, phân cấp parent_id và đối chiếu DDL schema.
    """
    print("-> [Transformer: skills] Xây dựng taxonomy 76 kỹ năng IT chuẩn hóa...")
    name_to_id = {}
    skill_rows = []

    # Bước 1: Gán skill_id (1-indexed) theo thứ tự
    for idx, item in enumerate(SKILLS_TAXONOMY):
        skill_id = idx + 1
        name_to_id[item["name"]] = skill_id

    # Bước 2: Chuyển đổi tên parent thành parent_id hợp lệ
    for idx, item in enumerate(SKILLS_TAXONOMY):
        skill_id = idx + 1
        parent_name = item["parent"]
        parent_id = name_to_id.get(parent_name, None) if parent_name else None

        skill_rows.append({
            "skill_id": skill_id,
            "parent_id": parent_id,
            "skill_name": item["name"],
            "skill_normalized": item["canonical"],
            "skill_category": item["cat"],
            "description": item["desc"],
            "is_active": True
        })

    print(f"   [Transformer: skills] Đã tạo thành công {len(skill_rows)} kỹ năng (trong đó có {sum(1 for s in skill_rows if s['parent_id'] is not None)} kỹ năng phân cấp).")
    return skill_rows

import os
import pytest
from pathlib import Path


@pytest.fixture
def sample_topcv_card_html() -> str:
    return """
    <div class="job-item-2" data-job-id="123456">
        <h3 class="title">
            <a href="https://www.topcv.vn/viec-lam/senior-python-developer/123456.html">
                Senior Python Developer
            </a>
        </h3>
        <a class="company">Tech Corp</a>
        <img class="avatar" src="https://cdn.topcv.vn/logo.png" />
        <label class="title-salary">25 - 35 triệu</label>
        <span class="address">Hà Nội</span>
        <span class="exp">3 năm</span>
        <div class="tag">
            <span class="item-tag" title="Python">Python</span>
            <span class="item-tag" title="Django">Django</span>
        </div>
        <span class="time">Hạn nộp: 30/11/2026</span>
    </div>
    """


@pytest.fixture
def sample_topcv_detail_html() -> str:
    return """
    <html>
        <body>
            <h1 class="job-detail__title">Senior Python Developer</h1>
            <div class="job-detail__company-title">Tech Corp</div>
            <div class="job-detail__info--section">
                <div class="job-detail__info--item-content-title">Hạn nộp hồ sơ</div>
                <div class="job-detail__info--item-content-value">30/11/2026</div>
            </div>
            <div class="job-description">
                <div class="job-description__item">
                    <h3>Mô tả công việc</h3>
                    <p>- Phát triển API sử dụng FastAPI và Django</p>
                </div>
                <div class="job-description__item">
                    <h3>Yêu cầu ứng viên</h3>
                    <p>- Có ít nhất 3 năm kinh nghiệm</p>
                </div>
                <div class="job-description__item">
                    <h3>Quyền lợi</h3>
                    <p>- Lương tháng 13, bảo hiểm đầy đủ</p>
                </div>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def sample_topdev_detail_html() -> str:
    return """
    <html>
        <head>
            <script>
                self.__next_f.push([1,"1:{\\"id\\":999,\\"title\\":\\"Data Engineer (PySpark)\\",\\"company\\":{\\"display_name\\":\\"Data Solutions Ltd\\",\\"description\\":\\"Data firm\\"}}\\n"])
            </script>
        </head>
        <body>
            <h1 class="text-2xl font-bold">Data Engineer (PySpark)</h1>
            <div class="company-name">Data Solutions Ltd</div>
            <div class="deadline">Còn 15 ngày</div>
            <div class="job-description">
                <h3>Job Description</h3>
                <p>Build ETL pipelines with Apache Spark and Airflow.</p>
            </div>
            <div class="job-requirements">
                <h3>Job Requirements</h3>
                <p>3+ years with Python, SQL, Spark.</p>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def sample_vnw_job_item() -> dict:
    return {
        "jobId": 987654,
        "jobTitle": "Backend Golang Engineer",
        "alias": "backend-golang-engineer",
        "companyName": "Fintech Vietnam",
        "companyLogo": "https://images.vietnamworks.com/logo.png",
        "companyId": 1024,
        "prettySalary": "$2000 - $3000",
        "yearsOfExperience": 3,
        "approvedOn": "2026-10-01T08:00:00Z",
        "expiredOn": "2026-11-01T23:59:59Z",
        "skills": [{"skillName": "Golang"}, {"skillName": "PostgreSQL"}, {"skillName": "Docker"}],
        "workingLocations": [{"address": "Quận 1, TP. Hồ Chí Minh", "cityNameVI": "Hồ Chí Minh"}],
        "jobDescription": "<p>Phát triển hệ thống microservices backend bằng Golang</p>",
        "jobRequirement": "<p>Tối thiểu 3 năm kinh nghiệm backend</p>",
        "benefits": [{"benefitValue": "13th month salary"}, {"benefitValue": "Premium health insurance"}]
    }

import pytest
import pandas as pd
from src.recommender.content_based import (
    compute_skill_score,
    compute_exp_score,
    compute_location_mode_score,
    compute_salary_score,
    compute_composite_score,
    generate_rationale,
    ContentBasedRecommender
)

def test_compute_skill_score():
    user_skills = ["Python", "SQL", "Docker"]
    req_skills = ["Python", "Docker", "Kubernetes"]
    # req: 2/3 (Python, Docker) -> 0.667
    score = compute_skill_score(user_skills, req_skills)
    assert score == 0.667

    # Khớp toàn bộ kỹ năng yêu cầu
    score_full = compute_skill_score(["SQL", "Power BI", "Excel"], ["SQL", "Power BI", "Excel"])
    assert score_full == 1.0

    # Không có kỹ năng yêu cầu
    score_empty = compute_skill_score(["SQL"], [])
    assert score_empty == 0.5

def test_compute_exp_score():
    # User 2 years, job [1, 3] -> 1.0
    assert compute_exp_score(2.0, 1.0, 3.0) == 1.0
    # User 0.5 year, job [1, 3] -> diff = -0.5 >= -1.0 -> 0.7
    assert compute_exp_score(0.5, 1.0, 3.0) == 0.7
    # User 7 years, job [1, 3] -> user_exp > job_max + 3 (7 > 6) -> 0.85
    assert compute_exp_score(7.0, 1.0, 3.0) == 0.85

def test_compute_location_mode_score():
    # Matching city and mode
    assert compute_location_mode_score("Hà Nội", ["Remote", "Hybrid"], "Hà Nội", "Remote") == 1.0
    # Matching city, not preferred mode (score_city=1.0, score_mode=0.2 -> 0.6)
    assert compute_location_mode_score("Hà Nội", ["Remote"], "Hà Nội", "Onsite") == 0.6
    # All cities, any mode
    assert compute_location_mode_score("Tất cả", None, "Đà Nẵng", "Onsite") == 1.0

def test_compute_salary_score():
    # Missing salary in job -> None
    assert compute_salary_score(20_000_000, None, None) is None
    # User expectation within or below job salary
    assert compute_salary_score(20_000_000, 25_000_000, 40_000_000) == 1.0
    # Job max below expectation
    assert compute_salary_score(30_000_000, 10_000_000, 20_000_000) == 0.667

def test_compute_composite_score():
    # Case with salary: all 1.0 -> 1.0
    score, used_w = compute_composite_score(1.0, 1.0, 1.0, 1.0, 1.0)
    assert score == 1.0
    assert used_w['sal'] == 0.10

    # Case without salary (dynamic re-weighting)
    score_nosal, used_w_nosal = compute_composite_score(1.0, 1.0, 1.0, 1.0, None)
    assert score_nosal == 1.0
    assert 'sal' not in used_w_nosal
    assert round(used_w_nosal['skills'], 4) == round(0.40 / 0.90, 4)

def test_generate_rationale():
    rationale = generate_rationale(
        matched_skills=["Python", "SQL"],
        missing_skills=["Kubernetes"],
        user_exp=2.0,
        job_min_exp=1.0,
        job_mode="Remote",
        is_salary_fit=True
    )
    assert "Khớp 2/3 kỹ năng" in rationale
    assert "Kinh nghiệm phù hợp" in rationale
    assert "Hình thức Remote" in rationale
    assert "Đạt kỳ vọng lương" in rationale

def test_recommender_pipeline():
    mock_data = pd.DataFrame([
        {
            'job_id': 'job_1',
            'title': 'Senior Python Developer',
            'description_clean': 'Lập trình Python backend phát triển ứng dụng phần mềm',
            'required_skills': 'Python, SQL, Docker',
            'preferred_skills': 'AWS',
            'experience_min': 2.0,
            'experience_max': 5.0,
            'city': 'Hà Nội',
            'work_mode': 'Hybrid',
            'salary_min': 25000000.0,
            'salary_max': 45000000.0,
            'is_active': True,
            'job_url': 'https://example.com/job1',
            'company_name': 'Tech Corp',
            'company_logo_url': ''
        },
        {
            'job_id': 'job_2',
            'title': 'Junior Python Backend Developer',
            'description_clean': 'Lập trình Python backend và cơ sở dữ liệu cho phần mềm',
            'required_skills': 'Python, SQL',
            'preferred_skills': 'Git',
            'experience_min': 1.0,
            'experience_max': 2.0,
            'city': 'Hà Nội',
            'work_mode': 'Hybrid',
            'salary_min': 15000000.0,
            'salary_max': 22000000.0,
            'is_active': True,
            'job_url': 'https://example.com/job2',
            'company_name': 'Software JSC',
            'company_logo_url': ''
        },
        {
            'job_id': 'job_3',
            'title': 'Java Backend Developer',
            'description_clean': 'Lập trình phát triển phần mềm hệ thống backend doanh nghiệp',
            'required_skills': 'Java, Spring Boot',
            'preferred_skills': 'MySQL',
            'experience_min': 3.0,
            'experience_max': 5.0,
            'city': 'Hồ Chí Minh',
            'work_mode': 'Onsite',
            'salary_min': 20000000.0,
            'salary_max': 30000000.0,
            'is_active': True,
            'job_url': 'https://example.com/job3',
            'company_name': 'Enterprise Corp',
            'company_logo_url': ''
        }
    ])
    
    rec = ContentBasedRecommender()
    rec.fit(mock_data)
    
    results = rec.recommend(
        target_title="Python Developer",
        cv_text="Lập trình Python backend phát triển phần mềm",
        skills=["Python", "SQL"],
        user_exp=2.0,
        preferred_city="Hà Nội",
        preferred_work_modes=["Hybrid"],
        min_salary=20000000.0,
        top_n=2
    )
    
    assert len(results) == 2
    top_job = results.iloc[0]
    assert "Python" in top_job['Tiêu đề']
    assert top_job['Tổng điểm (%)'] > 0
    assert "Khớp" in top_job['Lời giải thích']

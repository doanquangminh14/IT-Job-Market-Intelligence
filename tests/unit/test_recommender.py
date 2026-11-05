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
from src.data_cleaning.skill_canonical import SKILL_GROUPS, TECH_LOOKUP, split_skill_match

def test_compute_skill_score():
    user_skills = ["Python", "SQL", "Redis"]
    req_skills = ["Python", "Redis", "Kubernetes"]
    # coverage 2/3, hệ số tin cậy m/(m+1) = 2/3  ->  0.444 (Kubernetes không gần kỹ năng nào của hồ sơ)
    assert compute_skill_score(user_skills, req_skills) == 0.444
    assert compute_skill_score(user_skills, req_skills, mode='v2') == 0.444
    # công thức cũ (v1) chỉ lấy coverage
    assert compute_skill_score(user_skills, req_skills, mode='v1') == 0.667

    # Khớp toàn bộ 3 kỹ năng: coverage 1.0 x 3/4
    assert compute_skill_score(["SQL", "Power BI", "Excel"], ["SQL", "Power BI", "Excel"]) == 0.75

    # Job chỉ yêu cầu 1 kỹ năng và bạn có nó: KHÔNG còn đạt 100% (lỗi của công thức cũ)
    assert compute_skill_score(["Python"], ["Python"]) == 0.5
    assert compute_skill_score(["Python"], ["Python"], mode='v1') == 1.0

    # Job không liệt kê kỹ năng: không có dữ liệu (None), thay vì 0.5 giả
    assert compute_skill_score(["SQL"], []) is None
    assert compute_skill_score(["SQL"], [], mode='v1') == 0.5


def test_related_skills_get_partial_credit():
    # PostgreSQL ~ MySQL, Vue ~ React: mỗi kỹ năng gần nhau tính 0,5 ➔ m = 1, coverage 1/3, x 1/2
    user, req = ["PostgreSQL", "Vue"], ["MySQL", "React", "Docker"]
    assert split_skill_match(user, req) == ([], ["MySQL", "React"], ["Docker"])
    assert compute_skill_score(user, req, mode='v2') == 0.0
    assert compute_skill_score(user, req) == 0.167
    # khớp chính xác vẫn được ưu tiên hơn khớp gần
    assert compute_skill_score(["MySQL"], ["MySQL", "Docker"]) > compute_skill_score(["PostgreSQL"], ["MySQL", "Docker"]) > 0
    # tắt điểm gần nhau thì v3 == v2
    assert compute_skill_score(user, req, related_credit=0) == compute_skill_score(user, req, mode='v2')
    # kỹ năng đồng xuất hiện nhưng KHÔNG thay thế được nhau thì không được tính
    assert split_skill_match(["Python"], ["SQL"]) == ([], [], ["SQL"])


def test_related_skill_groups_use_canonical_names():
    """Mọi tên trong SKILL_GROUPS phải là tên chuẩn của từ điển, nếu không nhóm sẽ không bao giờ khớp."""
    canonical = {v.lower() for v in TECH_LOOKUP.values()}
    unknown = sorted({s for grp in SKILL_GROUPS for s in grp if s.lower() not in canonical})
    assert unknown == []


def test_rationale_mentions_related_skills():
    text = generate_rationale(["Python"], ["Docker"], 2.0, 1.0, "Onsite", True, related_skills=["MySQL"])
    assert "Khớp 1/3 kỹ năng" in text and "Gần với MySQL" in text

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
    # Tất cả điểm 1.0 -> 1.0, trọng số mặc định 0.30/0.40/0.10/0.10/0.10
    score, used_w = compute_composite_score(1.0, 1.0, 1.0, 1.0, 1.0)
    assert score == 1.0
    assert used_w == pytest.approx({'skills': 0.30, 'text': 0.40, 'exp': 0.10, 'loc': 0.10, 'sal': 0.10})

    # Thiếu lương: loại thành phần và co giãn lại trọng số
    score_nosal, used_w_nosal = compute_composite_score(1.0, 1.0, 1.0, 1.0, None)
    assert score_nosal == 1.0
    assert 'sal' not in used_w_nosal
    assert round(used_w_nosal['skills'], 4) == round(0.30 / 0.90, 4)

    # Job không liệt kê kỹ năng: cũng bị loại, không kéo điểm xuống
    score_noskill, w_noskill = compute_composite_score(None, 1.0, 1.0, 1.0, 1.0)
    assert score_noskill == 1.0 and 'skills' not in w_noskill
    assert abs(sum(w_noskill.values()) - 1.0) < 1e-9

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

def test_recommender_pipeline(tmp_path):
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
    
    # Dùng thư mục tạm + không lưu: tránh ghi đè model thật trong data/models/
    rec = ContentBasedRecommender(model_dir=str(tmp_path))
    rec.fit(mock_data, save_model=False)
    
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


def _mock_jobs():
    base = dict(preferred_skills='', experience_min=1.0, experience_max=3.0, city='Hà Nội', work_mode='Onsite',
                salary_min=None, salary_max=None, is_active=True, job_url='', company_name='X', company_logo_url='')
    return pd.DataFrame([
        dict(base, job_id='a', title='C++ Embedded Engineer', required_skills='C++, Linux', job_tags='Nhúng',
             description_clean='Lập trình C++ cho thiết bị nhúng, yêu cầu kinh nghiệm CI/CD'),
        dict(base, job_id='b', title='C# .NET Developer', required_skills='C#, .NET, SQL Server', job_tags='',
             description_clean='Phát triển ứng dụng .NET Core bằng C#'),
        dict(base, job_id='c', title='Kế toán', required_skills='', job_tags='Tài chính',
             description_clean='Hạch toán sổ sách'),
    ])


def test_engine_vectorizer_uses_tech_aware_tokenizer(tmp_path):
    """Hồi quy: vectorizer của engine phải giữ C++/C#/.NET khác nhau và giữ chữ tiếng Việt có dấu."""
    rec = ContentBasedRecommender(model_dir=str(tmp_path), min_df=1)
    rec.fit(_mock_jobs(), save_model=False)
    vocab = rec.tfidf_vectorizer.vocabulary_
    assert {'cpp', 'csharp', 'dotnet', 'cicd'} <= set(vocab)
    assert 'nghiệm' in vocab


def test_recommend_and_fit_report_are_consistent(tmp_path):
    rec = ContentBasedRecommender(model_dir=str(tmp_path), min_df=1)
    rec.fit(_mock_jobs(), save_model=False)
    kwargs = dict(target_title="C# .NET Developer", skills=["C#", ".NET"], user_exp=2.0, preferred_city="Hà Nội")
    res = rec.recommend(top_n=3, **kwargs)
    assert res.iloc[0]['job_id'] == 'b'
    report = rec.analyze_cv_fit_for_job('b', **kwargs)
    assert f"Tổng điểm: {res.iloc[0]['Tổng điểm (%)']:.1f}%" in report
    assert "Xếp hạng: 1/" in report


def test_job_without_skills_drops_skill_component(tmp_path):
    rec = ContentBasedRecommender(model_dir=str(tmp_path), min_df=1)
    rec.fit(_mock_jobs(), save_model=False)
    sc = rec.score_components(target_title="Kế toán", skills=["Python"])
    assert sc['comps'].loc[2, 'skills'] != sc['comps'].loc[2, 'skills']   # NaN: job không liệt kê kỹ năng
    res = rec.recommend(target_title="Kế toán", skills=["Python"], top_n=3)
    assert res.loc[res['job_id'] == 'c', 'Điểm kỹ năng (%)'].isna().all()

"""Dữ liệu mới / ngày mới phải được phản ánh: cờ is_active tính lại theo hôm nay, khóa cache đổi khi file dữ liệu đổi."""
import os
import time

import pandas as pd

from src.data_cleaning.freshness import refresh_is_active
from src.recommender import content_based as cb


def test_refresh_is_active_uses_today_not_stale_flag():
    df = pd.DataFrame({
        'deadline': ['2026-11-04', '2026-11-05', '2026-11-30', None, 'không rõ'],
        'is_active': [True, True, False, False, True],      # cờ cũ tính từ ngày khác
    })
    out = refresh_is_active(df, today=pd.Timestamp('2026-11-05 15:30'))
    # hết hạn hôm qua ➔ False; hạn đúng hôm nay ➔ còn hạn; hạn sau ➔ còn hạn; không có / không đọc được hạn ➔ giữ cờ cũ
    assert out['is_active'].tolist() == [False, True, True, False, True]
    assert df['is_active'].tolist() == [True, True, False, False, True]      # không sửa df gốc


def test_refresh_is_active_without_deadline_column():
    out = refresh_is_active(pd.DataFrame({'title': ['a', 'b']}))
    assert out['is_active'].tolist() == [True, True]


def test_data_file_version_changes_when_file_is_rewritten(tmp_path, monkeypatch):
    f = tmp_path / "jobs_clean.csv"
    f.write_text("job_id\n1\n", encoding="utf-8")
    monkeypatch.setattr(cb, "DEFAULT_DATA_CANDIDATES", [str(tmp_path / "missing.csv"), str(f)])
    v1 = cb.data_file_version()
    assert v1[0] == str(f)
    os.utime(f, (time.time() + 60, time.time() + 60))      # mô phỏng chạy lại notebook 02
    assert cb.data_file_version() != v1


def test_load_or_train_refreshes_active_flag(tmp_path, monkeypatch):
    jobs = pd.DataFrame({
        'job_id': ['a', 'b', 'c'], 'title': ['Python Developer', 'Java Developer', 'Data Engineer'],
        'required_skills': ['Python', 'Java', 'SQL'], 'job_tags': ['', '', ''],
        'description_clean': ['python django', 'java spring', 'sql spark'],
        'deadline': ['2000-01-01', '2999-01-01', '2999-01-01'], 'is_active': [True, True, True], 'is_it': [True, True, True],
        'company_name': ['X', 'Y', 'Z'], 'experience_min': [1.0, 1.0, 1.0], 'experience_max': [None, None, None],
        'city': ['Hà Nội'] * 3, 'work_mode': ['Onsite'] * 3, 'salary_min': [None] * 3, 'salary_max': [None] * 3,
    })
    path = tmp_path / "jobs.csv"
    jobs.to_csv(path, index=False)
    eng = cb.ContentBasedRecommender(model_dir=str(tmp_path / "models"), min_df=1)
    eng.load_or_train(str(path))
    assert eng.jobs_df.set_index('job_id')['is_active'].to_dict() == {'a': False, 'b': True, 'c': True}
    # tin hết hạn bị xếp cuối (điểm -1) nên không lọt vào top-2, dù khớp kỹ năng Python
    assert 'a' not in set(eng.recommend(skills=['Python', 'Java', 'SQL'], top_n=2)['job_id'])
    eng2 = cb.ContentBasedRecommender(model_dir=str(tmp_path / "models"), min_df=1)
    eng2.load_or_train(str(path), refresh_active=False)                                      # giữ cờ trong file
    assert eng2.jobs_df['is_active'].all()

"""CF (ALS + nhật ký tương tác) và Hybrid CBF + CF (notebook 07)."""
import numpy as np
import pandas as pd
import pytest

from src.recommender.collaborative import CFModel, InteractionLog, fold_in
from src.recommender.content_based import ContentBasedRecommender
from src.recommender.hybrid import MIN_USER_INTERACTIONS, HybridRecommender, cf_percentile, hybrid_scores


def _two_cluster_events():
    """20 người dùng: 10 người chỉ bấm tin nhóm A (a0-a4), 10 người chỉ bấm tin nhóm B (b0-b4)."""
    rows = []
    for u in range(20):
        group = "a" if u < 10 else "b"
        for j in range(5):
            if (u + j) % 3:                       # mỗi người bấm một phần của nhóm mình
                rows.append({"user_id": f"u{u}", "job_id": f"{group}{j}", "event": "save"})
    return pd.DataFrame(rows)


def test_interaction_log_roundtrip(tmp_path):
    log = InteractionLog(str(tmp_path))
    assert log.load_events().empty and log.version()[1] == 0.0
    log.log_event("alice", "job1", "save", position=0, source="CBF")
    log.log_event("alice", "job2", "apply")
    log.log_impressions("alice", ["job1", "job2", "job3"], source="recommend", mode="CBF")
    ev = log.load_events()
    assert ev[["user_id", "job_id", "event"]].values.tolist() == [["alice", "job1", "save"], ["alice", "job2", "apply"]]
    assert sorted(log.user_job_ids("alice")) == ["job1", "job2"]
    assert len(pd.read_csv(log.impressions_path)) == 3
    with pytest.raises(ValueError):
        log.log_event("alice", "job1", "like")


def test_cf_model_learns_clusters_and_marks_unknown_items():
    cf = CFModel({"k": 4}).fit(_two_cluster_events())
    assert cf.ready
    jobs = ["a0", "a1", "b0", "b1", "brand_new_job"]
    s = cf.score(cf.user_vector("u0"), jobs)            # u0 thuộc nhóm A
    assert np.isnan(s[-1])                              # tin chưa ai tương tác: CF không biết
    assert min(s[0], s[1]) > max(s[2], s[3])


def test_fold_in_new_user_without_retraining():
    cf = CFModel({"k": 4}).fit(_two_cluster_events())
    new_user = pd.DataFrame([{"user_id": "newbie", "job_id": "b2", "event": "apply"},
                             {"user_id": "newbie", "job_id": "b3", "event": "save"}])
    vec = cf.user_vector("newbie", new_user)            # không có trong mô hình ➔ fold-in
    s = cf.score(vec, ["a0", "a1", "b0", "b4"])
    assert min(s[2:]) > max(s[:2])
    assert cf.user_vector("ghost") is None              # không có lịch sử thì không có vector
    # fold-in đúng là một bước cập nhật ALS: với Y cố định, kết quả là nghiệm của hệ tuyến tính
    Y = np.eye(3)
    x = fold_in(Y, np.array([0]), np.array([3.0]), reg=0.0, alpha_conf=1.0)
    assert np.allclose(x, [1.0, 0.0, 0.0])


def test_hybrid_scores_rules():
    cbf = np.array([0.9, 0.5, 0.4, 0.3, 0.8])
    active = np.array([True, True, True, True, False])
    # Không có CF (toàn NaN) ➔ thứ tự giống hệt CBF; tin hết hạn = -inf
    h = hybrid_scores(cbf, np.full(5, np.nan), active)
    assert list(np.argsort(-h)[:4]) == [0, 1, 2, 3] and h[4] == -np.inf
    # CF rất thích tin 3 ➔ tin 3 được kéo lên; tin 0 không có CF (tin mới) vẫn giữ điểm nội dung
    cf = np.array([np.nan, 0.0, 0.0, 5.0, 0.0])
    h2 = hybrid_scores(cbf, cf, active)
    assert np.argsort(-h2)[0] in (0, 3) and h2[3] > h[3]
    assert h2[0] == pytest.approx(h[0])
    pct = cf_percentile(cf, active)
    assert np.isnan(pct[0]) and np.isnan(pct[4]) and pct[3] == 100.0


@pytest.fixture
def tiny_engine(tmp_path):
    jobs = pd.DataFrame({
        'job_id': [f"j{i}" for i in range(6)],
        'title': ['Python Developer', 'Python Backend', 'Data Engineer', 'Java Developer', 'Java Backend', 'QA Tester'],
        'required_skills': ['Python, Django', 'Python, FastAPI', 'Python, SQL', 'Java, Spring Boot', 'Java, SQL', 'Selenium'],
        'job_tags': [''] * 6, 'description_clean': ['python web', 'python api', 'data sql', 'java web', 'java api', 'testing'],
        'deadline': ['2999-01-01'] * 6, 'is_active': [True] * 6, 'is_it': [True] * 6,
        'company_name': list('ABCDEF'), 'experience_min': [1.0] * 6, 'experience_max': [None] * 6,
        'city': ['Hà Nội'] * 6, 'work_mode': ['Onsite'] * 6, 'salary_min': [None] * 6, 'salary_max': [None] * 6,
    })
    path = tmp_path / "jobs.csv"
    jobs.to_csv(path, index=False)
    eng = ContentBasedRecommender(model_dir=str(tmp_path / "models"), min_df=1)
    eng.load_or_train(str(path))
    return eng


def test_hybrid_falls_back_to_cbf_without_history(tiny_engine, tmp_path):
    log = InteractionLog(str(tmp_path / "log"))
    hyb = HybridRecommender(tiny_engine, log)
    df, info = hyb.recommend("alice", top_n=4, skills=["Python"])
    assert info["mode"] == "CBF" and "Điểm CF (%)" not in df.columns
    cbf_only = tiny_engine.recommend(skills=["Python"], top_n=4)
    assert df["job_id"].tolist() == cbf_only["job_id"].tolist()     # đúng thứ tự của CBF thuần


def test_hybrid_uses_cf_after_interactions_and_hides_seen_jobs(tiny_engine, tmp_path):
    log = InteractionLog(str(tmp_path / "log"))
    # 6 người dùng khác: ai thích j3 (Java) cũng thích j4; người dùng 'bob' đã quan tâm j3
    for u in range(6):
        for j in ("j3", "j4"):
            log.log_event(f"other{u}", j, "save")
        log.log_event(f"other{u}", "j0", "click")
    log.log_event("bob", "j3", "apply")
    assert MIN_USER_INTERACTIONS <= 1
    cf = CFModel({"k": 2}).fit(log.load_events())
    hyb = HybridRecommender(tiny_engine, log, cf_model=cf)
    df, info = hyb.recommend("bob", top_n=5, skills=["Python"])
    assert info["mode"] == "Hybrid" and info["n_interactions"] == 1
    assert "j3" not in df["job_id"].tolist()                          # tin đã ứng tuyển không bị gợi ý lại
    assert "Điểm CF (%)" in df.columns and df["Hạng"].tolist() == list(range(1, len(df) + 1))
    # CF: người giống bob (cùng thích j3) thích j4 nhiều hơn j0 ➔ điểm CF của j4 cao hơn
    cf_pct = df.set_index("job_id")["Điểm CF (%)"]
    assert cf_pct["j4"] > cf_pct["j0"]
    # và điểm Hybrid của j4 được nâng so với khi chỉ dùng nội dung (hồ sơ chỉ có Python nên j4 vẫn có thể đứng sau tin Python)
    sc, total = tiny_engine.score_all(skills=["Python"])
    ids = tiny_engine.jobs_df["job_id"].tolist()
    cf_raw = cf.score(cf.user_vector("bob"), ids)
    with_cf, without_cf = hybrid_scores(total, cf_raw, sc["active"]), hybrid_scores(total, np.full(len(ids), np.nan), sc["active"])
    assert with_cf[ids.index("j4")] > without_cf[ids.index("j4")]

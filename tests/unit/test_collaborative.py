import os
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

from src.recommender.collaborative import CollaborativeRecommender, get_cf_recommender
from src.recommender.synthetic_data import PERSONAS_DEF


def test_personas_definition_structure():
    assert len(PERSONAS_DEF) >= 8
    for p in PERSONAS_DEF:
        assert "id" in p
        assert "name" in p
        assert "skills" in p
        assert len(p["skills"]) > 0
        assert "seniorities" in p
        assert "target_share" in p


def test_cf_recommender_singleton():
    rec1 = get_cf_recommender()
    rec2 = get_cf_recommender()
    assert rec1 is rec2
    assert rec1.item_sim_matrix is not None


def test_cf_get_similar_jobs():
    rec = get_cf_recommender()
    # Lấy job đầu tiên có trong tập dữ liệu
    sample_job_id = next(iter(rec.job_to_idx.keys()))
    similar = rec.get_similar_jobs(sample_job_id, top_k=4)

    assert isinstance(similar, list)
    assert len(similar) <= 4
    for job in similar:
        assert "job_id" in job
        assert "title" in job
        assert "similarity_pct" in job
        assert job["job_id"] != sample_job_id


def test_cf_get_recommendations_for_persona():
    rec = get_cf_recommender()
    recs = rec.get_recommendations_for_persona("backend_java", top_n=5)

    assert isinstance(recs, list)
    assert len(recs) > 0
    for job in recs:
        assert "job_id" in job
        assert "title" in job
        assert "match_score" in job
        assert 50.0 <= job["match_score"] <= 100.0


def test_cf_fallback_when_job_unknown():
    rec = get_cf_recommender()
    # Dùng một ID không tồn tại trong từ điển ma trận
    unknown_id = 9999999
    sims = rec.get_similar_jobs(unknown_id, top_k=2)
    assert isinstance(sims, list)

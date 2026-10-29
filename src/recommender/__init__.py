"""
Recommender System Module.
Chuyên sâu mô hình Content-Based Filtering cho dữ liệu việc làm IT.
"""

from .content_based import ContentBasedRecommender, get_content_based_recommender

__all__ = [
    "ContentBasedRecommender",
    "get_content_based_recommender"
]

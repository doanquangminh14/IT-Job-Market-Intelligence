"""
Recommender System Module.
- content_based: Content-Based Filtering (notebook 05) — đang dùng làm nền của ứng dụng.
- collaborative: ALS cho phản hồi ngầm + nhật ký tương tác (notebook 06, 07).
- hybrid: kết hợp CBF + CF cho ứng dụng (notebook 07).
"""

from .content_based import ContentBasedRecommender, get_content_based_recommender
from .collaborative import CFModel, InteractionLog
from .hybrid import HybridRecommender

__all__ = [
    "ContentBasedRecommender",
    "get_content_based_recommender",
    "CFModel",
    "InteractionLog",
    "HybridRecommender",
]

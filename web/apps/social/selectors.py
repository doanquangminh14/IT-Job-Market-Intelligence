"""Lớp đọc dữ liệu cho trang Cộng đồng. View và template CHỈ đi qua đây.

Stage 1: đọc từ mock_data (dữ liệu demo). Stage 2 thay phần thân các hàm bằng truy vấn model,
giữ nguyên tên hàm và hình dạng đối tượng trả về để template không phải đổi.
"""
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from apps.jobs.models import Job

from . import mock_data


@dataclass(frozen=True)
class Author:
    username: str
    title: str = ""
    skills: tuple[str, ...] = ()
    bio: str = ""

    @property
    def initials(self) -> str:
        parts = [p for p in self.username.replace("_", ".").split(".") if p]
        return "".join(p[0] for p in parts[:2]).upper() or "?"


@dataclass
class Comment:
    id: int
    author: Author
    body: str
    created_at: datetime


@dataclass
class Post:
    id: int
    author: Author
    body: str
    created_at: datetime
    tags: list[str] = field(default_factory=list)
    job_id: int | None = None
    job: Job | None = None
    like_count: int = 0
    comments: list[Comment] = field(default_factory=list)

    @property
    def comment_count(self) -> int:
        return len(self.comments)


def _authors() -> dict[str, Author]:
    return {u["username"]: Author(u["username"], u["title"], tuple(u["skills"]), u["bio"]) for u in mock_data.USERS}


def _build_posts() -> list[Post]:
    authors = _authors()
    comments: dict[int, list[Comment]] = {}
    for c in mock_data.COMMENTS:
        comments.setdefault(c["post_id"], []).append(
            Comment(c["id"], authors[c["author"]], c["body"], c["created_at"]))
    posts = [Post(p["id"], authors[p["author"]], p["body"], p["created_at"], list(p["tags"]), p["job_id"],
                  like_count=p["like_count"], comments=sorted(comments.get(p["id"], []), key=lambda c: c.created_at))
             for p in mock_data.POSTS]
    posts.sort(key=lambda p: (p.created_at, p.id), reverse=True)
    return posts


def _attach_jobs(posts: list[Post]) -> list[Post]:
    """Gắn tin tuyển dụng thật (nếu còn tồn tại) bằng MỘT truy vấn; tin không tồn tại thì bỏ qua."""
    ids = {p.job_id for p in posts if p.job_id}
    if ids:
        jobs = Job.objects.select_related("company").in_bulk(ids)
        for p in posts:
            p.job = jobs.get(p.job_id)
    return posts


def list_posts(tag: str | None = None) -> list[Post]:
    posts = _build_posts()
    if tag:
        posts = [p for p in posts if any(t.lower() == tag.lower() for t in p.tags)]
    return _attach_jobs(posts)


def get_post(post_id: int) -> Post | None:
    post = next((p for p in _build_posts() if p.id == post_id), None)
    return _attach_jobs([post])[0] if post else None


def get_author(username: str) -> Author | None:
    return _authors().get(username)


def posts_by(username: str) -> list[Post]:
    return _attach_jobs([p for p in _build_posts() if p.author.username == username])


def follow_counts(username: str) -> dict:
    """Số người theo dõi / đang theo dõi (demo: suy ra từ FOLLOWING_SEED của người xem demo)."""
    followers = 1 if username in mock_data.FOLLOWING_SEED else 0
    return {"followers": followers, "following": 0}


def trending_tags(limit: int = 8) -> list[dict]:
    counts = Counter(t for p in _build_posts() for t in p.tags)
    return [{"name": n, "n": c} for n, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]]


def suggested_authors(exclude: str | None = None, limit: int = 3) -> list[Author]:
    return [a for a in _authors().values() if a.username != exclude][:limit]


def following_seed() -> list[str]:
    return list(mock_data.FOLLOWING_SEED)

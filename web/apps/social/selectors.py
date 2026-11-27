"""Lớp đọc dữ liệu cho trang Cộng đồng. View và template CHỈ đi qua đây.

Stage 2: đọc từ database. Giữ nguyên hình dạng đối tượng của Stage 1 (Author / Post / Comment)
để template không phụ thuộc vào model. Hồ sơ công khai CHỈ gồm username, chức danh, kỹ năng
(quyết định CEO, #002) — không bao giờ lộ email, lương mong muốn hay đoạn CV.
"""
from dataclasses import dataclass, field
from datetime import datetime

from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef, Q

from apps.jobs.models import Job, Skill

from .models import Follow, Like, Post as PostModel

PAGE_SIZE = 10


@dataclass(frozen=True)
class Author:
    username: str
    title: str = ""
    skills: tuple[str, ...] = ()

    @property
    def initials(self) -> str:
        parts = [p for p in self.username.replace("_", ".").replace("-", ".").split(".") if p]
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
    job: Job | None = None
    like_count: int = 0
    comment_count: int = 0
    liked: bool = False
    comments: list[Comment] = field(default_factory=list)


def _author(user) -> Author:
    """Chỉ lấy các trường được phép công khai."""
    profile = getattr(user, "profile", None)
    if profile is None:
        return Author(user.username)
    return Author(user.username, profile.desired_title, tuple(profile.skill_list))


def _visible_posts(viewer=None):
    qs = (PostModel.objects.filter(is_hidden=False, author__is_active=True)
          .select_related("author", "author__profile", "job", "job__company")
          .prefetch_related("tags")
          .annotate(n_likes=Count("likes", distinct=True),
                    n_comments=Count("comments", filter=Q(comments__is_hidden=False), distinct=True)))
    if viewer is not None and viewer.is_authenticated:
        qs = qs.annotate(is_liked=Exists(Like.objects.filter(post=OuterRef("pk"), user=viewer)))
    return qs


def _to_post(p) -> Post:
    return Post(p.id, _author(p.author), p.body, p.created_at, [t.name for t in p.tags.all()], p.job,
                like_count=p.n_likes, comment_count=p.n_comments, liked=getattr(p, "is_liked", False))


def feed_page(viewer=None, tag: str | None = None, following_only: bool = False, before: int | None = None) -> dict:
    """Một trang bảng tin, mới nhất trước. Phân trang keyset theo (created_at, id): O(log n + k) mỗi trang
    nhờ index social_post_feed_idx, không chậm dần khi lật sâu như OFFSET."""
    qs = _visible_posts(viewer)
    if tag:
        qs = qs.filter(id__in=PostModel.objects.filter(tags__name__iexact=tag).values("id"))
    if following_only and viewer is not None and viewer.is_authenticated:
        followed = Follow.objects.filter(follower=viewer).values("followee")
        qs = qs.filter(Q(author__in=followed) | Q(author=viewer))
    if before:
        cursor = PostModel.objects.filter(pk=before).values("created_at", "id").first()
        if cursor:  # con trỏ không hợp lệ → bỏ qua, trả trang đầu
            qs = qs.filter(Q(created_at__lt=cursor["created_at"]) |
                           Q(created_at=cursor["created_at"], id__lt=cursor["id"]))
    rows = list(qs.order_by("-created_at", "-id")[:PAGE_SIZE + 1])
    posts = [_to_post(p) for p in rows[:PAGE_SIZE]]
    return {"posts": posts, "next_before": posts[-1].id if len(rows) > PAGE_SIZE else None}


def get_post(post_id: int, viewer=None) -> Post | None:
    p = _visible_posts(viewer).filter(pk=post_id).first()
    if p is None:
        return None
    post = _to_post(p)
    post.comments = [Comment(c.id, _author(c.author), c.body, c.created_at)
                     for c in p.comments.filter(is_hidden=False, author__is_active=True)
                                        .select_related("author", "author__profile")]
    return post


def get_author(username: str):
    """Trả (user, Author) hoặc (None, None) nếu không tồn tại / bị khóa."""
    user = (get_user_model().objects.filter(username=username, is_active=True)
            .select_related("profile").first())
    return (user, _author(user)) if user else (None, None)


def posts_by(user, viewer=None, limit: int = 20) -> list[Post]:
    return [_to_post(p) for p in _visible_posts(viewer).filter(author=user).order_by("-created_at", "-id")[:limit]]


def profile_counts(user) -> dict:
    return {
        "posts": PostModel.objects.filter(author=user, is_hidden=False).count(),
        "followers": Follow.objects.filter(followee=user).count(),
        "following": Follow.objects.filter(follower=user).count(),
    }


def is_following(viewer, user) -> bool:
    return bool(viewer.is_authenticated and Follow.objects.filter(follower=viewer, followee=user).exists())


def followed_usernames(viewer) -> set[str]:
    if not viewer.is_authenticated:
        return set()
    return set(Follow.objects.filter(follower=viewer).values_list("followee__username", flat=True))


def trending_tags(limit: int = 8) -> list[dict]:
    rows = (Skill.objects.filter(posts__is_hidden=False).annotate(n=Count("posts", distinct=True))
            .order_by("-n", "name").values("name", "n")[:limit])
    return list(rows)


def suggested_authors(viewer=None, limit: int = 3) -> list[Author]:
    """Thành viên có bài viết gần đây, trừ chính mình và người đã theo dõi."""
    qs = (get_user_model().objects.filter(is_active=True, posts__is_hidden=False)
          .annotate(n=Count("posts", distinct=True)).order_by("-n", "username").select_related("profile"))
    if viewer is not None and viewer.is_authenticated:
        qs = qs.exclude(pk=viewer.pk).exclude(pk__in=Follow.objects.filter(follower=viewer).values("followee"))
    return [_author(u) for u in qs[:limit]]


def resolve_tags(raw: str) -> list:
    """Chỉ nhận chủ đề là kỹ năng ĐÃ CÓ trong hệ thống (allow-list), tối đa MAX_TAGS; bỏ qua tên lạ."""
    from .models import MAX_TAGS
    names = [t.strip()[:100] for t in raw.split(",") if t.strip()]
    found = []
    for name in names:
        skill = Skill.objects.filter(name__iexact=name).first()
        if skill and skill not in found:
            found.append(skill)
        if len(found) == MAX_TAGS:
            break
    return found

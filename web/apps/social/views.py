from functools import wraps
from urllib.parse import urlencode

from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render

from . import selectors

PAGE_SIZE = 10


def demo_only(view):
    """Stage 1: trang Cộng đồng chỉ chạy dữ liệu demo, nên tắt hẳn (404) khi COMMUNITY_DEMO tắt (production)."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not settings.COMMUNITY_DEMO:
            raise Http404("Trang Cộng đồng chưa mở.")
        return view(request, *args, **kwargs)
    return wrapper


def _known_ids(request, posts) -> dict:
    """Danh sách id hợp lệ cho social.js (để loại dữ liệu localStorage hỏng/lạ)."""
    return {
        "post_ids": [p.id for p in posts],
        "usernames": [a.username for a in selectors.suggested_authors(limit=100)],
        "following_seed": selectors.following_seed(),
        "me": request.user.username if request.user.is_authenticated else "",
    }


@demo_only
def feed(request):
    tag = request.GET.get("tag", "").strip()[:50]
    posts = selectors.list_posts(tag or None)
    page = Paginator(posts, PAGE_SIZE).get_page(request.GET.get("page"))  # trang ngoài phạm vi → trang cuối
    return render(request, "social/feed.html", {
        "page_obj": page,
        "tag": tag,
        "querystring": urlencode({"tag": tag}) if tag else "",
        "trending_tags": [{**t, "active": t["name"].lower() == tag.lower()} for t in selectors.trending_tags()],
        "suggested": selectors.suggested_authors(),
        "known": _known_ids(request, list(page)),
    })


@demo_only
def post_detail(request, pk):
    post = selectors.get_post(pk)
    if post is None:
        raise Http404("Không tìm thấy bài viết.")
    return render(request, "social/post_detail.html", {
        "post": post,
        "suggested": selectors.suggested_authors(exclude=post.author.username),
        "known": _known_ids(request, [post]),
    })


@demo_only
def profile(request, username):
    author = selectors.get_author(username)
    if author is None:
        raise Http404("Không tìm thấy thành viên.")
    posts = selectors.posts_by(username)
    return render(request, "social/profile.html", {
        "author": author,
        "posts": posts,
        "counts": {**selectors.follow_counts(username), "posts": len(posts)},
        "known": _known_ids(request, posts),
    })

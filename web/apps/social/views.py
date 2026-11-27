from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import selectors
from .models import COMMENT_MAX_LENGTH, POST_MAX_LENGTH, Comment, Follow, Like, Post, Report

# Giới hạn chống spam: tối đa N lần trong cửa sổ thời gian (đếm trực tiếp trong DB, không cần cache)
RATE_WINDOW = timedelta(minutes=10)
MAX_POSTS_PER_WINDOW = 5
MAX_COMMENTS_PER_WINDOW = 20


def _int_or_none(value):
    try:
        n = int(value)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _wants_json(request) -> bool:
    return "application/json" in request.headers.get("Accept", "")


def _back(request, fallback: str):
    """Quay lại trang trước, CHỈ khi là đường dẫn nội bộ (chống open redirect)."""
    nxt = request.POST.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()},
                                               require_https=request.is_secure()):
        return redirect(nxt)
    return redirect(fallback)


def _too_many(model, user, field="author") -> bool:
    since = timezone.now() - RATE_WINDOW
    limit = MAX_POSTS_PER_WINDOW if model is Post else MAX_COMMENTS_PER_WINDOW
    return model.objects.filter(**{field: user}, created_at__gte=since).count() >= limit


# ---------- Trang đọc (công khai) ----------

def feed(request):
    tag = request.GET.get("tag", "").strip()[:50]
    tab = "following" if request.GET.get("tab") == "following" and request.user.is_authenticated else "latest"
    page = selectors.feed_page(request.user, tag or None, following_only=(tab == "following"),
                               before=_int_or_none(request.GET.get("before")))
    base = {k: v for k, v in (("tag", tag), ("tab", tab if tab != "latest" else "")) if v}
    older_url = f"?{urlencode({**base, 'before': page['next_before']})}" if page["next_before"] else ""
    return render(request, "social/feed.html", {
        "posts": page["posts"],
        "older_url": older_url,
        "is_first_page": not request.GET.get("before"),
        "first_page_url": f"?{urlencode(base)}",
        "tag": tag,
        "tab": tab,
        "tab_urls": {"latest": f"?{urlencode({k: v for k, v in base.items() if k != 'tab'})}",
                     "following": f"?{urlencode({**base, 'tab': 'following'})}"},
        "trending_tags": [{**t, "active": t["name"].lower() == tag.lower()} for t in selectors.trending_tags()],
        "suggested": selectors.suggested_authors(request.user),
        "post_max": POST_MAX_LENGTH,
    })


def post_detail(request, pk):
    post = selectors.get_post(pk, request.user)
    if post is None:
        raise Http404("Không tìm thấy bài viết.")
    return render(request, "social/post_detail.html", {
        "post": post,
        "report_reasons": Report.Reason.choices,
        "comment_max": COMMENT_MAX_LENGTH,
        "suggested": selectors.suggested_authors(request.user),
    })


def profile(request, username):
    user, author = selectors.get_author(username)
    if user is None:
        raise Http404("Không tìm thấy thành viên.")
    return render(request, "social/profile.html", {
        "profile_user": user,
        "author": author,
        "posts": selectors.posts_by(user, request.user),
        "counts": selectors.profile_counts(user),
        "is_following": selectors.is_following(request.user, user),
    })


# ---------- Thao tác ghi (đăng nhập + POST + CSRF) ----------

@login_required
@require_POST
def create_post(request):
    body = request.POST.get("body", "").strip()
    if not body:
        messages.error(request, "Hãy viết nội dung trước khi đăng.")
    elif len(body) > POST_MAX_LENGTH:
        messages.error(request, f"Bài viết tối đa {POST_MAX_LENGTH} ký tự.")
    elif _too_many(Post, request.user):
        messages.error(request, "Bạn đăng bài quá nhanh. Vui lòng thử lại sau ít phút.")
    else:
        post = Post.objects.create(author=request.user, body=body)
        post.tags.set(selectors.resolve_tags(request.POST.get("tags", "")))
        messages.success(request, "Đã đăng bài viết.")
        return redirect("community:post", pk=post.pk)
    return _back(request, reverse("community:feed"))


@login_required
@require_POST
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk, is_hidden=False)
    body = request.POST.get("body", "").strip()
    url = reverse("community:post", args=[post.pk])
    if not body:
        messages.error(request, "Bình luận không được để trống.")
    elif len(body) > COMMENT_MAX_LENGTH:
        messages.error(request, f"Bình luận tối đa {COMMENT_MAX_LENGTH} ký tự.")
    elif _too_many(Comment, request.user):
        messages.error(request, "Bạn bình luận quá nhanh. Vui lòng thử lại sau ít phút.")
    else:
        Comment.objects.create(post=post, author=request.user, body=body)
        return redirect(f"{url}#comments")
    return redirect(url)


@login_required
@require_POST
def toggle_like(request, pk):
    post = get_object_or_404(Post, pk=pk, is_hidden=False)
    deleted, _ = Like.objects.filter(user=request.user, post=post).delete()
    if not deleted:
        try:
            with transaction.atomic():
                Like.objects.create(user=request.user, post=post)
        except IntegrityError:  # bấm 2 lần cùng lúc: đã có sẵn
            pass
    liked = not deleted
    if _wants_json(request):
        return JsonResponse({"pressed": liked, "count": post.likes.count()})
    return _back(request, reverse("community:post", args=[post.pk]))


@login_required
@require_POST
def toggle_follow(request, username):
    user, _ = selectors.get_author(username)
    if user is None:
        raise Http404("Không tìm thấy thành viên.")
    if user == request.user:
        if _wants_json(request):
            return JsonResponse({"error": "Không thể tự theo dõi chính mình."}, status=400)
        messages.error(request, "Không thể tự theo dõi chính mình.")
        return _back(request, reverse("community:profile", args=[username]))
    deleted, _ = Follow.objects.filter(follower=request.user, followee=user).delete()
    if not deleted:
        try:
            with transaction.atomic():
                Follow.objects.create(follower=request.user, followee=user)
        except IntegrityError:
            pass
    following = not deleted
    if _wants_json(request):
        return JsonResponse({"pressed": following, "count": Follow.objects.filter(followee=user).count()})
    return _back(request, reverse("community:profile", args=[username]))


@login_required
@require_POST
def report_post(request, pk):
    post = get_object_or_404(Post, pk=pk, is_hidden=False)
    reason = request.POST.get("reason", "")
    if reason not in Report.Reason.values:
        messages.error(request, "Hãy chọn lý do báo cáo.")
    else:
        _, created = Report.objects.get_or_create(reporter=request.user, post=post, defaults={"reason": reason})
        messages.success(request, "Cảm ơn bạn, báo cáo đã được ghi nhận." if created
                         else "Bạn đã báo cáo bài viết này trước đó.")
    return redirect("community:post", pk=post.pk)

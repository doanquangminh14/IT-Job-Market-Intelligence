"""Nạp dữ liệu DEMO cho trang Cộng đồng từ apps/social/mock_data.py.

Chỉ chạy khi settings.COMMUNITY_DEMO bật (mặc định = DEBUG) để production không bao giờ có bài giả.
Chạy lại nhiều lần an toàn: tài khoản demo đã có thì bỏ qua (không tạo trùng bài).
Tài khoản demo không đăng nhập được (mật khẩu vô hiệu), email đuôi @demo.local.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Profile
from apps.jobs.models import Skill
from apps.social import mock_data
from apps.social.models import Comment, Follow, Like, Post

DEMO_EMAIL_DOMAIN = "demo.local"


class Command(BaseCommand):
    help = "Nạp bài viết / thành viên demo cho trang Cộng đồng (chỉ khi COMMUNITY_DEMO bật)."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.COMMUNITY_DEMO:
            raise CommandError("COMMUNITY_DEMO đang tắt (production). Không nạp dữ liệu demo.")
        User = get_user_model()
        if User.objects.filter(email__endswith=f"@{DEMO_EMAIL_DOMAIN}").exists():
            self.stdout.write("Dữ liệu demo đã có, bỏ qua.")
            return

        users = {}
        for u in mock_data.USERS:
            user = User(username=u["username"], email=f"{u['username']}@{DEMO_EMAIL_DOMAIN}")
            user.set_unusable_password()
            user.save()
            Profile.objects.create(user=user, desired_title=u["title"], skills=", ".join(u["skills"]))
            users[u["username"]] = user

        posts = {}
        for p in mock_data.POSTS:
            post = Post.objects.create(author=users[p["author"]], body=p["body"])
            Post.objects.filter(pk=post.pk).update(created_at=p["created_at"])  # giữ thứ tự thời gian của demo
            post.tags.set(Skill.objects.filter(name__in=p["tags"]))
            posts[p["id"]] = post
            # Lượt thích: lấy lần lượt các thành viên demo khác, không vượt số người có thật
            likers = [x for name, x in users.items() if name != p["author"]][:p["like_count"]]
            Like.objects.bulk_create([Like(user=x, post=post) for x in likers])

        for c in mock_data.COMMENTS:
            comment = Comment.objects.create(post=posts[c["post_id"]], author=users[c["author"]], body=c["body"])
            Comment.objects.filter(pk=comment.pk).update(created_at=c["created_at"])

        names = list(users)
        for i, name in enumerate(names):  # mỗi người theo dõi 2 người kế tiếp
            for other in (names[(i + 1) % len(names)], names[(i + 2) % len(names)]):
                Follow.objects.get_or_create(follower=users[name], followee=users[other])

        self.stdout.write(self.style.SUCCESS(
            f"Đã nạp {len(users)} thành viên, {len(posts)} bài viết, {len(mock_data.COMMENTS)} bình luận demo."))

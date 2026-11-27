"""Model trang Cộng đồng (thảo luận #002, Stage 2). Migration chỉ THÊM bảng mới, không đụng bảng cũ."""
from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models
from django.db.models import F, Q

POST_MAX_LENGTH = 2000
COMMENT_MAX_LENGTH = 1000
MAX_TAGS = 5


class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts",
                               verbose_name="Tác giả")
    body = models.TextField("Nội dung", validators=[MaxLengthValidator(POST_MAX_LENGTH)])
    tags = models.ManyToManyField("jobs.Skill", related_name="posts", blank=True, verbose_name="Chủ đề")
    job = models.ForeignKey("jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="shared_in",
                            verbose_name="Tin tuyển dụng được chia sẻ")
    is_hidden = models.BooleanField("Đã ẩn (kiểm duyệt)", default=False, db_index=True)
    created_at = models.DateTimeField("Thời gian đăng", auto_now_add=True)

    class Meta:
        verbose_name = "Bài viết"
        verbose_name_plural = "Bài viết"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["-created_at", "-id"], name="social_post_feed_idx"),
            models.Index(fields=["author", "-created_at"], name="social_post_author_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.author} – {self.body[:50]}"


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments", verbose_name="Bài viết")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_comments",
                               verbose_name="Tác giả")
    body = models.TextField("Nội dung", validators=[MaxLengthValidator(COMMENT_MAX_LENGTH)])
    is_hidden = models.BooleanField("Đã ẩn (kiểm duyệt)", default=False)
    created_at = models.DateTimeField("Thời gian", auto_now_add=True)

    class Meta:
        verbose_name = "Bình luận"
        verbose_name_plural = "Bình luận"
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["post", "created_at"], name="social_comment_post_idx")]

    def __str__(self) -> str:
        return f"{self.author}: {self.body[:50]}"


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_likes")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lượt thích"
        verbose_name_plural = "Lượt thích"
        constraints = [models.UniqueConstraint(fields=["user", "post"], name="unique_post_like")]


class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following_set")
    followee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="follower_set")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Theo dõi"
        verbose_name_plural = "Theo dõi"
        constraints = [
            models.UniqueConstraint(fields=["follower", "followee"], name="unique_follow"),
            models.CheckConstraint(condition=~Q(follower=F("followee")), name="no_self_follow"),
        ]


class Report(models.Model):
    class Reason(models.TextChoices):
        SPAM = "spam", "Spam / quảng cáo"
        OFFENSIVE = "offensive", "Xúc phạm / thù ghét"
        MISLEADING = "misleading", "Sai sự thật / lừa đảo"
        OTHER = "other", "Lý do khác"

    class Status(models.TextChoices):
        OPEN = "open", "Chờ xử lý"
        REVIEWED = "reviewed", "Đã xử lý"
        DISMISSED = "dismissed", "Bỏ qua"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_reports",
                                 verbose_name="Người báo cáo")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reports", verbose_name="Bài viết")
    reason = models.CharField("Lý do", max_length=20, choices=Reason.choices)
    status = models.CharField("Trạng thái", max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    created_at = models.DateTimeField("Thời gian", auto_now_add=True)

    class Meta:
        verbose_name = "Báo cáo vi phạm"
        verbose_name_plural = "Báo cáo vi phạm"
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["reporter", "post"], name="unique_post_report")]

    def __str__(self) -> str:
        return f"{self.get_reason_display()} – bài #{self.post_id}"

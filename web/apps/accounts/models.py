from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """User tùy biến ngay từ đầu để sau này thêm trường không phải migrate lại bảng auth."""
    email = models.EmailField("Email", unique=True)

    class Meta:
        verbose_name = "Người dùng"
        verbose_name_plural = "Người dùng"


class Profile(models.Model):
    """Hồ sơ ứng viên: chính là đầu vào của hệ gợi ý CBF (chức danh, kỹ năng, kinh nghiệm, thành phố, hình thức, lương)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    desired_title = models.CharField("Chức danh mong muốn", max_length=200, blank=True)
    skills = models.CharField("Kỹ năng", max_length=500, blank=True, help_text="Ngăn cách bằng dấu phẩy, vd. Python, SQL, Django")
    years_experience = models.FloatField("Số năm kinh nghiệm", default=0)
    preferred_city = models.CharField("Thành phố mong muốn", max_length=100, blank=True)
    preferred_work_mode = models.CharField("Hình thức làm việc", max_length=20, blank=True)
    min_salary = models.PositiveIntegerField("Lương mong muốn tối thiểu (triệu VNĐ)", null=True, blank=True)
    bio = models.TextField("Giới thiệu / đoạn CV", blank=True)

    class Meta:
        verbose_name = "Hồ sơ"
        verbose_name_plural = "Hồ sơ"

    def __str__(self) -> str:
        return f"Hồ sơ của {self.user}"

    @property
    def skill_list(self) -> list[str]:
        return [s.strip() for s in self.skills.split(",") if s.strip()]

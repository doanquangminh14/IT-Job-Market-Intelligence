from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Company(models.Model):
    name = models.CharField("Tên công ty", max_length=255, unique=True)
    logo_url = models.URLField("Logo", max_length=500, blank=True)

    class Meta:
        verbose_name = "Công ty"
        verbose_name_plural = "Công ty"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Skill(models.Model):
    name = models.CharField("Kỹ năng", max_length=100, unique=True)

    class Meta:
        verbose_name = "Kỹ năng"
        verbose_name_plural = "Kỹ năng"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class JobQuerySet(models.QuerySet):
    def active(self):
        """Tin còn hạn theo NGÀY HÔM NAY (giống src.data_cleaning.freshness): deadline >= hôm nay hoặc không có deadline."""
        today = timezone.localdate()
        return self.filter(models.Q(deadline__gte=today) | models.Q(deadline__isnull=True))

    def it_only(self):
        return self.filter(is_it=True)


class Job(models.Model):
    class EmploymentType(models.TextChoices):
        FULL_TIME = "Full-time", "Toàn thời gian"
        PART_TIME = "Part-time", "Bán thời gian"
        INTERN = "Intern", "Thực tập"
        CONTRACT = "Contract", "Hợp đồng"

    class WorkMode(models.TextChoices):
        ONSITE = "Onsite", "Tại văn phòng"
        REMOTE = "Remote", "Từ xa"
        HYBRID = "Hybrid", "Kết hợp"

    job_id = models.CharField("Mã tin", max_length=100, unique=True, help_text="Mã gốc, vd. topcv_2314643")
    source = models.CharField("Nguồn", max_length=50, db_index=True)
    title = models.CharField("Chức danh", max_length=300)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="jobs", verbose_name="Công ty")
    description = models.TextField("Mô tả", blank=True)
    skills = models.ManyToManyField(Skill, related_name="jobs", blank=True, verbose_name="Kỹ năng yêu cầu")
    tags = models.CharField("Thẻ ngành", max_length=500, blank=True)
    experience_min = models.FloatField("Kinh nghiệm tối thiểu (năm)", null=True, blank=True)
    experience_max = models.FloatField("Kinh nghiệm tối đa (năm)", null=True, blank=True)
    location = models.CharField("Địa chỉ", max_length=500, blank=True)
    city = models.CharField("Thành phố", max_length=100, blank=True, db_index=True)
    salary_min = models.BigIntegerField("Lương tối thiểu (VNĐ/tháng)", null=True, blank=True)
    salary_max = models.BigIntegerField("Lương tối đa (VNĐ/tháng)", null=True, blank=True)
    employment_type = models.CharField("Loại hình", max_length=20, choices=EmploymentType.choices, blank=True)
    work_mode = models.CharField("Hình thức", max_length=20, choices=WorkMode.choices, blank=True)
    deadline = models.DateField("Hạn nộp", null=True, blank=True, db_index=True)
    is_it = models.BooleanField("Thuộc ngành IT", default=True, db_index=True)
    job_url = models.URLField("Link gốc", max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = JobQuerySet.as_manager()

    class Meta:
        verbose_name = "Tin tuyển dụng"
        verbose_name_plural = "Tin tuyển dụng"
        ordering = ["-deadline", "-id"]

    def __str__(self) -> str:
        return f"{self.title} – {self.company}"

    def get_absolute_url(self) -> str:
        return reverse("jobs:detail", args=[self.pk])

    @property
    def is_active(self) -> bool:
        return self.deadline is None or self.deadline >= timezone.localdate()

    @property
    def tag_list(self) -> list[str]:
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def salary_display(self) -> str:
        """Hiển thị lương theo triệu VNĐ, vd. '15 - 25 triệu', 'Từ 20 triệu', 'Thỏa thuận'."""
        def m(v):
            return f"{v / 1_000_000:g}"
        if self.salary_min and self.salary_max:
            if self.salary_min == self.salary_max:
                return f"{m(self.salary_min)} triệu"
            return f"{m(self.salary_min)} - {m(self.salary_max)} triệu"
        if self.salary_min:
            return f"Từ {m(self.salary_min)} triệu"
        if self.salary_max:
            return f"Đến {m(self.salary_max)} triệu"
        return "Thỏa thuận"

    @property
    def experience_display(self) -> str:
        lo, hi = self.experience_min, self.experience_max
        if lo is None and hi is None:
            return "Không yêu cầu"
        if not lo and not hi:
            return "Không yêu cầu"
        if hi and lo != hi:
            return f"{lo or 0:g} - {hi:g} năm"
        return f"Từ {lo or hi:g} năm"


class SavedJob(models.Model):
    """Tin người dùng đã lưu (bookmark). Về sau có thể dùng làm tín hiệu tương tác cho Collaborative Filtering."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_jobs")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tin đã lưu"
        verbose_name_plural = "Tin đã lưu"
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "job"], name="unique_saved_job")]

    def __str__(self) -> str:
        return f"{self.user} ♥ {self.job_id}"

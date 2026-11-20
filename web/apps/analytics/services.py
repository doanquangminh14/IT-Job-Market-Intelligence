"""Các phép thống kê thị trường việc làm, tính bằng Django ORM. Tách khỏi views để tái sử dụng (trang chủ, API sau này)."""
from django.db.models import Avg, Count, Q

from apps.jobs.models import Job, Skill


def base_queryset(active_only: bool = False):
    qs = Job.objects.it_only()
    return qs.active() if active_only else qs


def overview(qs) -> dict:
    with_salary = qs.filter(Q(salary_min__isnull=False) | Q(salary_max__isnull=False))
    return {
        "total_jobs": qs.count(),
        "active_jobs": qs.active().count(),
        "companies": qs.values("company").distinct().count(),
        "skills": Skill.objects.filter(jobs__in=qs).distinct().count(),
        "salary_share": round(100 * with_salary.count() / qs.count()) if qs.exists() else 0,
    }


def top_skills(qs, limit: int = 15) -> list[dict]:
    return list(Skill.objects.filter(jobs__in=qs)
                .annotate(n=Count("jobs")).order_by("-n", "name")
                .values("name", "n")[:limit])


def count_by(qs, field: str, limit: int | None = None) -> list[dict]:
    rows = qs.exclude(**{field: ""}).values(field).annotate(n=Count("id")).order_by("-n")
    rows = rows[:limit] if limit else rows
    return [{"label": r[field], "n": r["n"]} for r in rows]


def salary_by_city(qs, limit: int = 6) -> list[dict]:
    """Lương trung bình (triệu VNĐ/tháng) theo thành phố, chỉ trên tin có cả mức sàn và trần."""
    rows = (qs.filter(salary_min__isnull=False, salary_max__isnull=False).exclude(city="")
            .values("city").annotate(n=Count("id"), lo=Avg("salary_min"), hi=Avg("salary_max"))
            .filter(n__gte=5).order_by("-n")[:limit])
    return [{"label": r["city"], "n": r["n"], "lo": round(r["lo"] / 1e6, 1), "hi": round(r["hi"] / 1e6, 1)}
            for r in rows]


def top_companies(qs, limit: int = 10) -> list[dict]:
    rows = qs.values("company__name").annotate(n=Count("id")).order_by("-n")[:limit]
    return [{"label": r["company__name"], "n": r["n"]} for r in rows]

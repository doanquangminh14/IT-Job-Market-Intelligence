"""Các phép thống kê thị trường việc làm, tính bằng Django ORM. Tách khỏi views để tái sử dụng (trang chủ, API sau này)."""
from collections import defaultdict
from statistics import median

from django.db.models import Count, Max, Q

from apps.jobs.models import EXPERIENCE_CHOICES, Job, Skill, active_q, experience_q

MIN_SAMPLE = 5  # Số tin tối thiểu để hiển thị một con số lương (tránh kết luận từ mẫu quá nhỏ)

_DISPLAY = {
    "work_mode": dict(Job.WorkMode.choices),
    "employment_type": dict(Job.EmploymentType.choices),
}


def parse_filters(params) -> dict:
    """Đọc bộ lọc từ GET theo danh sách cho phép. Giá trị không hợp lệ bị bỏ qua (không gây lỗi)."""
    filters = {"active": params.get("active") == "1"}
    city = params.get("city", "").strip()
    if city and Job.objects.it_only().filter(city=city).exists():
        filters["city"] = city
    if params.get("work_mode") in Job.WorkMode.values:
        filters["work_mode"] = params["work_mode"]
    if params.get("employment_type") in Job.EmploymentType.values:
        filters["employment_type"] = params["employment_type"]
    if experience_q(params.get("experience", "")) is not None:
        filters["experience"] = params["experience"]
    skill = params.get("skill", "").strip()[:100]
    if skill:
        name = Skill.objects.filter(name__iexact=skill).values_list("name", flat=True).first()
        if name:
            filters["skill"] = name
    return filters


def base_queryset(active_only: bool = False, filters: dict | None = None):
    qs = Job.objects.it_only()
    filters = filters or {}
    if active_only or filters.get("active"):
        qs = qs.active()
    for field in ("city", "work_mode", "employment_type"):
        if filters.get(field):
            qs = qs.filter(**{field: filters[field]})
    if filters.get("experience"):
        qs = qs.filter(experience_q(filters["experience"]))
    if filters.get("skill"):
        # Lọc qua subquery để mỗi tin chỉ xuất hiện một lần (không nhân bản do join kỹ năng)
        qs = qs.filter(id__in=Job.objects.filter(skills__name__iexact=filters["skill"]).values("id"))
    return qs


def overview(qs) -> dict:
    """Các chỉ số tổng quan, gom trong một truy vấn aggregate (cộng một truy vấn đếm kỹ năng)."""
    agg = qs.aggregate(
        total=Count("id"),
        active=Count("id", filter=active_q()),
        companies=Count("company", distinct=True),
        salary_any=Count("id", filter=Q(salary_min__isnull=False) | Q(salary_max__isnull=False)),
        salary_both=Count("id", filter=Q(salary_min__isnull=False, salary_max__isnull=False)),
        last_import=Max("updated_at"),
    )
    total = agg["total"]
    return {
        "total_jobs": total,
        "active_jobs": agg["active"],
        "companies": agg["companies"],
        "skills": Skill.objects.filter(jobs__in=qs).distinct().count(),
        "salary_share": round(100 * agg["salary_any"] / total) if total else 0,
        "salary_range_share": round(100 * agg["salary_both"] / total) if total else 0,
        "last_import": agg["last_import"],
    }


def top_skills(qs, limit: int = 15, exclude: str | None = None) -> list[dict]:
    rows = Skill.objects.filter(jobs__in=qs)
    if exclude:
        rows = rows.exclude(name__iexact=exclude)
    return list(rows.annotate(n=Count("jobs")).order_by("-n", "name").values("name", "n")[:limit])


def count_by(qs, field: str, limit: int | None = None) -> list[dict]:
    """Đếm tin theo một trường. 'value' là giá trị gốc (dùng cho link lọc), 'label' là nhãn hiển thị."""
    rows = qs.exclude(**{field: ""}).values(field).annotate(n=Count("id")).order_by("-n", field)
    rows = rows[:limit] if limit else rows
    names = _DISPLAY.get(field, {})
    return [{"label": names.get(r[field], r[field]), "value": r[field], "n": r["n"]} for r in rows]


def _million(v: float) -> float:
    return round(v / 1e6, 1)


def salary_stats(qs, limit: int = 6) -> dict:
    """Lương trung vị (triệu VNĐ/tháng) trên các tin có cả mức sàn và mức trần, trong một truy vấn.

    - overall: trung vị của điểm giữa (sàn + trần) / 2; None nếu ít hơn MIN_SAMPLE tin.
    - by_city: trung vị mức sàn và mức trần theo thành phố, chỉ giữ thành phố có >= MIN_SAMPLE tin.
    Độ phức tạp O(N log N) trên N tin đã lọc (sắp xếp để lấy trung vị).
    """
    rows = qs.filter(salary_min__isnull=False, salary_max__isnull=False).values_list("city", "salary_min", "salary_max")
    mids, by_city = [], defaultdict(lambda: ([], []))
    for city, lo, hi in rows:
        mids.append((lo + hi) / 2)
        if city:
            by_city[city][0].append(lo)
            by_city[city][1].append(hi)
    overall = {"n": len(mids), "median": _million(median(mids)) if len(mids) >= MIN_SAMPLE else None}
    cities = [{"label": c, "value": c, "n": len(lo), "lo": _million(median(lo)), "hi": _million(median(hi))}
              for c, (lo, hi) in by_city.items() if len(lo) >= MIN_SAMPLE]
    cities.sort(key=lambda r: (-r["n"], r["label"]))
    return {"overall": overall, "by_city": cities[:limit]}


def salary_by_city(qs, limit: int = 6) -> list[dict]:
    return salary_stats(qs, limit)["by_city"]


def top_companies(qs, limit: int = 10) -> list[dict]:
    rows = (qs.values("company_id", "company__name").annotate(n=Count("id"))
            .order_by("-n", "company__name")[:limit])
    return [{"label": r["company__name"], "value": r["company_id"], "n": r["n"]} for r in rows]


EXPERIENCE_LABELS = dict(EXPERIENCE_CHOICES)

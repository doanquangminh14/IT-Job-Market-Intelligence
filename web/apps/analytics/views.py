from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse

from apps.jobs.models import Job

from . import services

FILTER_FIELDS = ("city", "work_mode", "employment_type", "experience")


def _list_url(filters: dict, **extra) -> str:
    """Link sang trang Việc làm với ĐÚNG bộ lọc của dashboard, để số tin ở danh sách khớp số trên biểu đồ.
    Luôn gửi f=1 và it_only/active_only tường minh, vì trang Việc làm có mặc định riêng (chỉ tin còn hạn)."""
    params = {"f": "1", "it_only": "on"}
    if filters.get("active"):
        params["active_only"] = "on"
    params.update({k: filters[k] for k in FILTER_FIELDS if filters.get(k)})
    if filters.get("skill"):
        params["skill"] = filters["skill"]
    params.update(extra)
    return f"{reverse('jobs:list')}?{urlencode(params)}"


def _with_urls(rows: list[dict], filters: dict, param: str) -> list[dict]:
    return [{**r, "url": _list_url(filters, **{param: r["value"]})} for r in rows]


def _summary(filters: dict) -> list[str]:
    labels = {
        "work_mode": dict(Job.WorkMode.choices),
        "employment_type": dict(Job.EmploymentType.choices),
        "experience": services.EXPERIENCE_LABELS,
    }
    parts = ["Chỉ tin còn hạn"] if filters.get("active") else []
    for key in FILTER_FIELDS:
        if filters.get(key):
            parts.append(labels.get(key, {}).get(filters[key], filters[key]))
    if filters.get("skill"):
        parts.append(f"Kỹ năng: {filters['skill']}")
    return parts


@login_required
def dashboard(request):
    filters = services.parse_filters(request.GET)
    qs = services.base_queryset(filters=filters)
    skill = filters.get("skill")
    salary = services.salary_stats(qs)

    # Khi đang lọc theo kỹ năng X: biểu đồ kỹ năng thành "kỹ năng đi kèm X" (bỏ X), link giữ X và thêm kỹ năng được bấm
    skill_rows = services.top_skills(qs, 15, exclude=skill)
    skill_param = "with_skill" if skill else "skill"
    skills = [{"label": r["name"], "n": r["n"], "url": _list_url(filters, **{skill_param: r["name"]})}
              for r in skill_rows]

    clear_skill = {k: v for k, v in filters.items() if k not in ("skill", "active") and v}
    if filters.get("active"):
        clear_skill["active"] = "1"

    context = {
        "filters": filters,
        "clear_skill_query": urlencode(clear_skill),
        "summary": _summary(filters),
        "overview": services.overview(qs),
        "salary_overall": salary["overall"],
        "min_sample": services.MIN_SAMPLE,
        "city_choices": (Job.objects.it_only().exclude(city="").values_list("city", flat=True)
                         .order_by("city").distinct()),
        "work_mode_choices": Job.WorkMode.choices,
        "employment_choices": Job.EmploymentType.choices,
        "experience_choices": services.EXPERIENCE_CHOICES,
        "charts": {
            "skills": skills,
            "cities": _with_urls(services.count_by(qs, "city", 8), filters, "city"),
            "work_modes": _with_urls(services.count_by(qs, "work_mode"), filters, "work_mode"),
            "employment_types": _with_urls(services.count_by(qs, "employment_type"), filters, "employment_type"),
            "sources": services.count_by(qs, "source"),
            # Không gắn link: N ở đây chỉ đếm tin có khoảng lương, khác số tin của danh sách theo thành phố
            "salary_by_city": salary["by_city"],
            "companies": _with_urls(services.top_companies(qs, 10), filters, "company"),
        },
    }
    return render(request, "analytics/dashboard.html", context)

from django.shortcuts import render

from . import services


def dashboard(request):
    active_only = request.GET.get("active") == "1"
    qs = services.base_queryset(active_only)
    context = {
        "active_only": active_only,
        "overview": services.overview(qs),
        "charts": {
            "skills": services.top_skills(qs, 15),
            "cities": services.count_by(qs, "city", 8),
            "work_modes": services.count_by(qs, "work_mode"),
            "employment_types": services.count_by(qs, "employment_type"),
            "sources": services.count_by(qs, "source"),
            "salary_by_city": services.salary_by_city(qs),
            "companies": services.top_companies(qs, 10),
        },
    }
    return render(request, "analytics/dashboard.html", context)

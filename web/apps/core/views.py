from django.db.models import F
from django.shortcuts import render

from apps.analytics import services
from apps.jobs.models import Job


def home(request):
    qs = Job.objects.it_only().active()
    context = {
        "stats": services.overview(Job.objects.it_only()),
        "top_skills": services.top_skills(qs, 12),
        "latest_jobs": qs.select_related("company").prefetch_related("skills")
                         .order_by(F("deadline").desc(nulls_last=True), "-id")[:6],
    }
    return render(request, "core/home.html", context)


def about(request):
    return render(request, "core/about.html")

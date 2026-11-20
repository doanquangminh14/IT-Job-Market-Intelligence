from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import JobFilterForm
from .models import Job, SavedJob, Skill

PAGE_SIZE = 20


def _filter_data(request):
    """Lần đầu mở trang (chưa bấm Lọc) thì bật sẵn 'Chỉ ngành IT' và 'Chỉ tin còn hạn'.
    Form có trường ẩn f=1, nên khi đã lọc thì checkbox bỏ trống nghĩa là tắt."""
    data = request.GET.copy()
    if "f" not in data:
        data.setdefault("it_only", "on")
        data.setdefault("active_only", "on")
    return data


def job_list(request):
    cities = (Job.objects.exclude(city="").values_list("city", flat=True)
              .order_by("city").distinct())
    form = JobFilterForm(_filter_data(request), cities=cities)
    jobs = Job.objects.select_related("company").prefetch_related("skills")

    if form.is_valid():
        cd = form.cleaned_data
        if cd["it_only"]:
            jobs = jobs.it_only()
        if cd["active_only"]:
            jobs = jobs.active()
        if cd["q"]:
            q = cd["q"]
            jobs = jobs.filter(Q(title__icontains=q) | Q(company__name__icontains=q)
                               | Q(skills__name__iexact=q) | Q(tags__icontains=q)).distinct()
        if cd["city"]:
            jobs = jobs.filter(city=cd["city"])
        if cd["skill"]:
            jobs = jobs.filter(skills__name__iexact=cd["skill"].strip())
        if cd["work_mode"]:
            jobs = jobs.filter(work_mode=cd["work_mode"])
        if cd["employment_type"]:
            jobs = jobs.filter(employment_type=cd["employment_type"])
        if cd["min_salary"]:
            # Tin có mức trần (hoặc mức sàn nếu không có trần) đạt mức lương mong muốn
            v = cd["min_salary"] * 1_000_000
            jobs = jobs.filter(Q(salary_max__gte=v) | Q(salary_max__isnull=True, salary_min__gte=v))
        sort = cd["sort"] or "newest"
    else:
        sort = "newest"

    if sort == "salary":
        jobs = jobs.order_by(F("salary_max").desc(nulls_last=True), F("salary_min").desc(nulls_last=True), "-id")
    elif sort == "title":
        jobs = jobs.order_by("title")
    else:
        jobs = jobs.order_by(F("deadline").desc(nulls_last=True), "-id")

    page = Paginator(jobs, PAGE_SIZE).get_page(request.GET.get("page"))

    # Giữ nguyên bộ lọc khi chuyển trang
    params = request.GET.copy()
    params.pop("page", None)

    saved_ids = set()
    if request.user.is_authenticated:
        saved_ids = set(request.user.saved_jobs.values_list("job_id", flat=True))

    context = {
        "form": form,
        "page_obj": page,
        "querystring": params.urlencode(),
        "saved_ids": saved_ids,
        "skill_options": Skill.objects.annotate(n=Count("jobs")).order_by("-n").values_list("name", flat=True)[:200],
    }
    return render(request, "jobs/job_list.html", context)


def job_detail(request, pk):
    job = get_object_or_404(Job.objects.select_related("company").prefetch_related("skills"), pk=pk)
    skill_ids = list(job.skills.values_list("id", flat=True))
    similar = (Job.objects.active().it_only().exclude(pk=job.pk)
               .filter(skills__in=skill_ids)
               .annotate(shared=Count("skills"))
               .order_by("-shared", F("deadline").desc(nulls_last=True))
               .select_related("company")[:5]) if skill_ids else []

    is_saved = False
    profile_skills = []
    if request.user.is_authenticated:
        is_saved = SavedJob.objects.filter(user=request.user, job=job).exists()
        profile = getattr(request.user, "profile", None)
        if profile:
            profile_skills = [s.lower() for s in profile.skill_list]

    job_skills = [s.name for s in job.skills.all()]
    context = {
        "job": job,
        "similar_jobs": similar,
        "is_saved": is_saved,
        "matched_skills": [s for s in job_skills if s.lower() in profile_skills],
        "missing_skills": [s for s in job_skills if s.lower() not in profile_skills] if profile_skills else [],
        "has_profile_skills": bool(profile_skills),
    }
    return render(request, "jobs/job_detail.html", context)


@login_required
@require_POST
def toggle_save(request, pk):
    job = get_object_or_404(Job, pk=pk)
    saved, created = SavedJob.objects.get_or_create(user=request.user, job=job)
    if created:
        messages.success(request, f"Đã lưu: {job.title}")
    else:
        saved.delete()
        messages.info(request, f"Đã bỏ lưu: {job.title}")
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()},
                                                    require_https=request.is_secure()):
        return redirect(next_url)
    return redirect(job.get_absolute_url())


@login_required
def saved_jobs(request):
    saved = (SavedJob.objects.filter(user=request.user)
             .select_related("job", "job__company").prefetch_related("job__skills"))
    saved = list(saved)
    return render(request, "jobs/saved_jobs.html",
                  {"saved_list": saved, "saved_ids": {s.job_id for s in saved}})

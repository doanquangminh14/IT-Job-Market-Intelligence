from django.test import TestCase
from django.urls import reverse

from apps.analytics import services
from apps.jobs.models import Job

from .factories import make_job, make_user


class PageSmokeTests(TestCase):
    def test_pages_render_without_data(self):
        for name in ("core:home", "core:about", "jobs:list", "accounts:login", "accounts:register"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(reverse("analytics:dashboard")).status_code, 200)

    def test_pages_render_with_data(self):
        job = make_job(salary_min=10_000_000, salary_max=20_000_000)
        self.assertContains(self.client.get(reverse("core:home")), job.title)
        self.assertContains(self.client.get(reverse("jobs:list")), job.title)
        self.client.force_login(make_user())
        self.assertContains(self.client.get(reverse("analytics:dashboard")), "chart-data")
        self.assertEqual(self.client.get(reverse("analytics:dashboard"), {"active": "1"}).status_code, 200)


class AnalyticsServiceTests(TestCase):
    def test_overview_and_top_skills(self):
        make_job(skills=("Python", "SQL"), salary_min=10_000_000, salary_max=20_000_000)
        make_job(company="Beta", skills=("Python",))
        make_job(skills=("Java",), days_left=-1)
        make_job(skills=("Excel",), is_it=False)

        qs = services.base_queryset()
        ov = services.overview(qs)
        self.assertEqual((ov["total_jobs"], ov["active_jobs"], ov["companies"], ov["skills"]), (3, 2, 2, 3))
        self.assertEqual(ov["salary_share"], 33)
        self.assertEqual(services.top_skills(qs)[0], {"name": "Python", "n": 2})
        self.assertEqual(services.base_queryset(active_only=True).count(), 2)
        self.assertEqual(services.count_by(qs, "city"), [{"label": "Hà Nội", "value": "Hà Nội", "n": 3}])
        self.assertEqual(Job.objects.count(), 4)

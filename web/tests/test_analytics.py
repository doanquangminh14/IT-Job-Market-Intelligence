"""Test cho trang Phân tích thị trường (thảo luận #001, Stage 1 / R1)."""
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.analytics import services
from apps.jobs.models import Job, experience_q

from .factories import make_job, make_user

URL = reverse("analytics:dashboard")
QUERY_BUDGET = 16  # Tổng số truy vấn tối đa cho một lần tải dashboard (gồm session + user)


def make_market():
    """Bộ dữ liệu nhỏ: 3 tin IT (1 hết hạn) + 1 tin non-IT."""
    a = make_job("Python Dev", skills=("Python", "SQL"), experience_min=0.2,
                 salary_min=10_000_000, salary_max=20_000_000)
    b = make_job("Django Dev", company="Beta", skills=("Python", "Django"), city="Hồ Chí Minh",
                 work_mode=Job.WorkMode.REMOTE, experience_min=2)
    c = make_job("Java Intern", skills=("Java",), employment_type=Job.EmploymentType.INTERN,
                 experience_min=5, days_left=-3)
    d = make_job("Kế toán", skills=("Excel",), is_it=False)
    return a, b, c, d


class DashboardAccessTests(TestCase):
    def test_requires_login(self):
        resp = self.client.get(URL)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:login"), resp["Location"])

    def test_renders_for_logged_in_user(self):
        make_market()
        self.client.force_login(make_user())
        resp = self.client.get(URL)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "chart-data")
        self.assertContains(resp, "vendor/chartjs/chart.umd.min.js")
        self.assertNotContains(resp, "npm/chart.js")  # Chart.js không còn tải từ CDN (Bootstrap vẫn dùng CDN, ngoài phạm vi R1)


class DashboardFilterTests(TestCase):
    def setUp(self):
        make_market()
        self.client.force_login(make_user())

    def total(self, **params):
        resp = self.client.get(URL, params)
        self.assertEqual(resp.status_code, 200)
        return resp.context["overview"]["total_jobs"]

    def test_default_is_all_it_jobs(self):
        self.assertEqual(self.total(), 3)

    def test_each_filter(self):
        cases = {
            "active": ({"active": "1"}, 2),
            "city": ({"city": "Hồ Chí Minh"}, 1),
            "work_mode": ({"work_mode": "Remote"}, 1),
            "employment_type": ({"employment_type": "Intern"}, 1),
            "experience <1": ({"experience": "0"}, 1),
            "experience 5+": ({"experience": "5+"}, 1),
            "skill (case-insensitive)": ({"skill": "python"}, 2),
        }
        for name, (params, expected) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.total(**params), expected)

    def test_invalid_values_are_ignored(self):
        self.assertEqual(self.total(city="Paris", work_mode="Moon", employment_type="x",
                                    experience="99", skill="NoSuchSkill", active="yes"), 3)

    def test_skill_filter_shows_co_occurring_skills(self):
        resp = self.client.get(URL, {"skill": "python"})
        labels = [r["label"] for r in resp.context["charts"]["skills"]]
        self.assertNotIn("Python", labels)
        self.assertEqual(sorted(labels), ["Django", "SQL"])
        self.assertContains(resp, "Kỹ năng đi kèm Python")

    def test_summary_and_vietnamese_labels(self):
        resp = self.client.get(URL, {"work_mode": "Remote", "active": "1"})
        self.assertEqual(resp.context["summary"], ["Chỉ tin còn hạn", "Từ xa"])
        labels = [r["label"] for r in resp.context["charts"]["work_modes"]]
        self.assertEqual(labels, ["Từ xa"])

    def test_query_budget(self):
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(URL, {"skill": "python", "city": "Hà Nội", "active": "1"})
        self.assertLessEqual(len(ctx), QUERY_BUDGET)


class ClickThroughParityTests(TestCase):
    """Số tin trên biểu đồ phải bằng số tin của trang Việc làm khi bấm vào."""

    def setUp(self):
        make_market()
        make_job("Data Engineer", company="Beta", skills=("Python", "SQL"), city="Hồ Chí Minh", experience_min=3)
        self.client.force_login(make_user())

    def assert_parity(self, params):
        charts = self.client.get(URL, params).context["charts"]
        checked = 0
        for chart in ("skills", "cities", "work_modes", "employment_types", "companies"):
            for row in charts[chart]:
                with self.subTest(params=params, chart=chart, label=row["label"]):
                    resp = self.client.get(row["url"])
                    self.assertEqual(resp.context["page_obj"].paginator.count, row["n"])
                    checked += 1
        self.assertGreater(checked, 0)

    def test_parity_without_filters(self):
        self.assert_parity({})

    def test_parity_with_filters(self):
        self.assert_parity({"active": "1"})
        self.assert_parity({"skill": "python", "experience": "1-2"})
        self.assert_parity({"city": "Hồ Chí Minh", "work_mode": "Remote"})


class AnalyticsServiceTests(TestCase):
    def test_tie_order_is_deterministic(self):
        make_job(company="Zeta", city="Đà Nẵng")
        make_job(company="Alpha", city="Cần Thơ")
        qs = services.base_queryset()
        self.assertEqual([r["label"] for r in services.count_by(qs, "city")], ["Cần Thơ", "Đà Nẵng"])
        self.assertEqual([r["label"] for r in services.top_companies(qs)], ["Alpha", "Zeta"])

    def test_salary_median_needs_min_sample(self):
        for i in range(services.MIN_SAMPLE - 1):
            make_job(salary_min=(10 + 2 * i) * 1_000_000, salary_max=(20 + 2 * i) * 1_000_000)
        stats = services.salary_stats(services.base_queryset())
        self.assertIsNone(stats["overall"]["median"])
        self.assertEqual(stats["by_city"], [])

        make_job(salary_min=18_000_000, salary_max=28_000_000)  # đủ 5 tin: sàn 10..18, trần 20..28
        stats = services.salary_stats(services.base_queryset())
        self.assertEqual(stats["overall"], {"n": 5, "median": 19.0})
        self.assertEqual(stats["by_city"], [{"label": "Hà Nội", "value": "Hà Nội", "n": 5, "lo": 14.0, "hi": 24.0}])

    def test_overview_salary_coverage(self):
        make_job(salary_min=10_000_000, salary_max=20_000_000)
        make_job(salary_min=15_000_000)
        make_job()
        make_job()
        ov = services.overview(services.base_queryset())
        self.assertEqual((ov["salary_share"], ov["salary_range_share"]), (50, 25))
        self.assertIsNotNone(ov["last_import"])

    def test_experience_bands(self):
        jobs = {v: make_job(experience_min=v) for v in (0, 0.2, 1, 2.5, 3, 4.9, 5, 10, None)}
        expected = {"0": {0, 0.2}, "1-2": {1, 2.5}, "3-4": {3, 4.9}, "5+": {5, 10}, "none": {None}}
        for band, values in expected.items():
            with self.subTest(band=band):
                got = set(Job.objects.filter(experience_q(band)))
                self.assertEqual(got, {jobs[v] for v in values})
        self.assertIsNone(experience_q("bogus"))

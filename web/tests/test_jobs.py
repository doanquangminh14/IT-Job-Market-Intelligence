import io
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.jobs.models import Job, SavedJob

from .factories import make_job, make_user


class JobModelTests(TestCase):
    def test_salary_and_experience_display(self):
        job = make_job(salary_min=15_000_000, salary_max=25_000_000, experience_min=1, experience_max=3)
        self.assertEqual(job.salary_display, "15 - 25 triệu")
        self.assertEqual(job.experience_display, "1 - 3 năm")
        self.assertEqual(make_job().salary_display, "Thỏa thuận")
        self.assertEqual(make_job(salary_min=20_000_000).salary_display, "Từ 20 triệu")

    def test_active_uses_today(self):
        live, expired, no_deadline = make_job(days_left=3), make_job(days_left=-1), make_job(days_left=None)
        active = set(Job.objects.active())
        self.assertEqual(active, {live, no_deadline})
        self.assertFalse(expired.is_active)


class JobListTests(TestCase):
    def setUp(self):
        self.py = make_job("Python Developer", skills=("Python", "Django"), salary_max=30_000_000)
        self.js = make_job("Frontend Developer", company="Beta", skills=("JavaScript", "React"),
                           city="Hồ Chí Minh", work_mode=Job.WorkMode.REMOTE)
        self.expired = make_job("Old Java Job", skills=("Java",), days_left=-5)
        self.non_it = make_job("Kế toán", skills=(), is_it=False)

    def get(self, **params):
        return self.client.get(reverse("jobs:list"), params)

    def test_defaults_hide_expired_and_non_it(self):
        jobs = set(self.get().context["page_obj"])
        self.assertEqual(jobs, {self.py, self.js})

    def test_unchecking_filters_shows_all(self):
        jobs = set(self.get(f=1).context["page_obj"])
        self.assertEqual(jobs, {self.py, self.js, self.expired, self.non_it})

    def test_keyword_matches_title_company_and_skill(self):
        self.assertEqual(list(self.get(q="python").context["page_obj"]), [self.py])
        self.assertEqual(list(self.get(q="beta").context["page_obj"]), [self.js])
        self.assertEqual(list(self.get(q="react").context["page_obj"]), [self.js])

    def test_filters(self):
        self.assertEqual(list(self.get(city="Hồ Chí Minh").context["page_obj"]), [self.js])
        self.assertEqual(list(self.get(work_mode="Remote").context["page_obj"]), [self.js])
        self.assertEqual(list(self.get(skill="django").context["page_obj"]), [self.py])
        self.assertEqual(list(self.get(min_salary=25).context["page_obj"]), [self.py])

    def test_pagination_keeps_filters(self):
        for i in range(25):
            make_job(f"Python job {i}")
        resp = self.get(q="python")
        self.assertEqual(resp.context["page_obj"].paginator.count, 26)
        self.assertContains(resp, "?q=python&page=2")


class JobDetailTests(TestCase):
    def test_detail_shows_skill_match_and_similar(self):
        job = make_job("Python Developer", skills=("Python", "SQL", "Docker"))
        other = make_job("Data Engineer", skills=("Python", "SQL"))
        user = make_user(skills="python, sql")
        self.client.force_login(user)
        resp = self.client.get(job.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(sorted(resp.context["matched_skills"]), ["Python", "SQL"])
        self.assertEqual(resp.context["missing_skills"], ["Docker"])
        self.assertIn(other, list(resp.context["similar_jobs"]))

    def test_404(self):
        self.assertEqual(self.client.get(reverse("jobs:detail", args=[999999])).status_code, 404)


class SaveJobTests(TestCase):
    def setUp(self):
        self.job = make_job()
        self.user = make_user()

    def test_requires_login_and_post(self):
        url = reverse("jobs:toggle_save", args=[self.job.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertFalse(SavedJob.objects.exists())
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_toggle_and_saved_list(self):
        self.client.force_login(self.user)
        url = reverse("jobs:toggle_save", args=[self.job.pk])
        self.client.post(url)
        self.assertTrue(SavedJob.objects.filter(user=self.user, job=self.job).exists())
        self.assertContains(self.client.get(reverse("jobs:saved")), self.job.title)
        self.client.post(url)
        self.assertFalse(SavedJob.objects.exists())

    def test_rejects_external_next(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("jobs:toggle_save", args=[self.job.pk]), {"next": "https://evil.com/"})
        self.assertRedirects(resp, self.job.get_absolute_url())


CSV_HEADER = ("job_id,company_name,title,description_clean,required_skills,job_tags,experience_min,experience_max,"
              "location,city,salary_min,salary_max,employment_type,work_mode,deadline,is_active,is_it,job_url,"
              "company_logo_url\n")


class ImportJobsCommandTests(TestCase):
    def write_csv(self, rows):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8-sig")
        tmp.write(CSV_HEADER + "".join(rows))
        tmp.close()
        self.addCleanup(Path(tmp.name).unlink)
        return tmp.name

    def test_import_and_upsert(self):
        path = self.write_csv([
            'topcv_1,Acme,Python Dev,"Mô tả, có dấu phẩy","Python, SQL","IT - Phần mềm",1,3,HN,Hà Nội,'
            '15000000,25000000,Full-time,Onsite,2099-01-01,True,True,https://x.vn/1,\n',
            'vietnamworks_2,Beta,Kế toán,,,,,,,Hồ Chí Minh,,,Full-time,Onsite,,True,False,https://x.vn/2,\n',
        ])
        call_command("import_jobs", path=path, stdout=io.StringIO())
        self.assertEqual(Job.objects.count(), 2)
        job = Job.objects.get(job_id="topcv_1")
        self.assertEqual(job.source, "topcv")
        self.assertEqual(job.salary_max, 25_000_000)
        self.assertEqual(sorted(job.skills.values_list("name", flat=True)), ["Python", "SQL"])
        self.assertFalse(Job.objects.get(job_id="vietnamworks_2").is_it)

        # Chạy lại với dữ liệu đổi ➔ cập nhật, không nhân bản
        path2 = self.write_csv([
            'topcv_1,Acme,Senior Python Dev,,Python,,,,,Hà Nội,,,Full-time,Remote,2099-01-01,True,True,,\n',
        ])
        call_command("import_jobs", path=path2, stdout=io.StringIO())
        self.assertEqual(Job.objects.count(), 2)
        job.refresh_from_db()
        self.assertEqual(job.title, "Senior Python Dev")
        self.assertEqual(job.work_mode, "Remote")
        self.assertEqual(list(job.skills.values_list("name", flat=True)), ["Python"])

"""
Nạp dữ liệu việc làm đã làm sạch (jobs_clean.csv do notebook 02 / src.data_cleaning.job_cleaner sinh ra) vào database.

    python manage.py import_jobs                      # tự tìm file trong settings.JOB_DATA_CANDIDATES
    python manage.py import_jobs --path đường/dẫn.csv
    python manage.py import_jobs --clear              # xóa toàn bộ tin cũ trước khi nạp

Chạy lại nhiều lần được: tin đã có (theo job_id) được cập nhật, tin mới được thêm vào.
"""
import csv
import sys
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.jobs.models import Company, Job, Skill

BATCH_SIZE = 1000


def _float(v):
    try:
        return float(v) if v not in ("", None) else None
    except ValueError:
        return None


def _int(v):
    f = _float(v)
    return int(f) if f is not None else None


def _date(v):
    try:
        return date.fromisoformat(str(v)[:10]) if v else None
    except ValueError:
        return None


def _bool(v, default=True):
    if v in ("", None):
        return default
    return str(v).strip().lower() in {"true", "1", "yes"}


def _split(v):
    return list(dict.fromkeys(s.strip() for s in (v or "").split(",") if s.strip() and s.strip().lower() != "nan"))


class Command(BaseCommand):
    help = "Nạp jobs_clean.csv vào database (upsert theo job_id)."

    def add_arguments(self, parser):
        parser.add_argument("--path", help="Đường dẫn file CSV. Mặc định: file đầu tiên tồn tại trong JOB_DATA_CANDIDATES.")
        parser.add_argument("--clear", action="store_true", help="Xóa toàn bộ tin tuyển dụng trước khi nạp.")

    def handle(self, *args, **opts):
        path = Path(opts["path"]) if opts["path"] else next(
            (p for p in settings.JOB_DATA_CANDIDATES if Path(p).exists()), None)
        if not path or not path.exists():
            raise CommandError("Không tìm thấy file dữ liệu sạch. Chạy notebook 02 hoặc "
                               "`python -m src.data_cleaning.job_cleaner` trước, hoặc truyền --path.")

        csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
        with open(path, encoding="utf-8-sig", newline="") as fh:
            # Trùng job_id trong file thì giữ dòng sau cùng
            rows = list({r["job_id"].strip(): r for r in csv.DictReader(fh) if (r.get("job_id") or "").strip()}.values())
        self.stdout.write(f"Đọc {len(rows):,} dòng từ {path}")

        with transaction.atomic():
            if opts["clear"]:
                Job.objects.all().delete()
            self._import(rows)

        self.stdout.write(self.style.SUCCESS(
            f"Xong: {Job.objects.count():,} tin, {Company.objects.count():,} công ty, {Skill.objects.count():,} kỹ năng."))

    def _import(self, rows):
        # 1. Công ty và kỹ năng: tạo các bản ghi còn thiếu
        company_names = {(r.get("company_name") or "Không rõ").strip() for r in rows}
        logos = {}
        for r in rows:
            name = (r.get("company_name") or "Không rõ").strip()
            if r.get("company_logo_url") and name not in logos:
                logos[name] = r["company_logo_url"].strip()
        Company.objects.bulk_create([Company(name=n, logo_url=logos.get(n, "")) for n in company_names],
                                    ignore_conflicts=True, batch_size=BATCH_SIZE)
        companies = dict(Company.objects.values_list("name", "id"))

        skill_names = {s for r in rows for s in _split(r.get("required_skills"))}
        Skill.objects.bulk_create([Skill(name=s) for s in skill_names], ignore_conflicts=True, batch_size=BATCH_SIZE)
        skills = {name.lower(): pk for name, pk in Skill.objects.values_list("name", "id")}

        # 2. Tin tuyển dụng: upsert theo job_id
        jobs = []
        for r in rows:
            jid = r["job_id"].strip()
            jobs.append(Job(
                job_id=jid,
                source=jid.split("_", 1)[0] if "_" in jid else "unknown",
                title=(r.get("title") or "").strip()[:300],
                company_id=companies[(r.get("company_name") or "Không rõ").strip()],
                description=r.get("description_clean") or "",
                tags=", ".join(_split(r.get("job_tags")))[:500],
                experience_min=_float(r.get("experience_min")),
                experience_max=_float(r.get("experience_max")),
                location=(r.get("location") or "")[:500],
                city=(r.get("city") or "").strip(),
                salary_min=_int(r.get("salary_min")),
                salary_max=_int(r.get("salary_max")),
                employment_type=(r.get("employment_type") or "").strip(),
                work_mode=(r.get("work_mode") or "").strip(),
                deadline=_date(r.get("deadline")),
                is_it=_bool(r.get("is_it")),
                job_url=(r.get("job_url") or "").strip(),
            ))
        update_fields = [f.name for f in Job._meta.concrete_fields
                         if f.name not in {"id", "job_id", "created_at"}]
        Job.objects.bulk_create(jobs, update_conflicts=True, unique_fields=["job_id"],
                                update_fields=update_fields, batch_size=BATCH_SIZE)

        # 3. Quan hệ Job–Skill: ghi lại từ đầu cho các tin vừa nạp
        job_pk = dict(Job.objects.filter(job_id__in=[j.job_id for j in jobs]).values_list("job_id", "id"))
        Through = Job.skills.through
        Through.objects.filter(job_id__in=job_pk.values()).delete()
        links = [Through(job_id=job_pk[r["job_id"].strip()], skill_id=skills[s.lower()])
                 for r in rows for s in _split(r.get("required_skills")) if s.lower() in skills]
        Through.objects.bulk_create(links, ignore_conflicts=True, batch_size=BATCH_SIZE * 5)

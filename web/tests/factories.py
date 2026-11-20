"""Hàm tạo dữ liệu mẫu dùng chung cho các test."""
from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import Profile, User
from apps.jobs.models import Company, Job, Skill

_counter = {"n": 0}


def make_user(username="alice", password="S3cure-pass!", **profile):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password=password)
    Profile.objects.create(user=user, **profile)
    return user


def make_job(title="Python Developer", company="Acme", skills=("Python", "SQL"), days_left=10, **fields):
    _counter["n"] += 1
    defaults = {
        "job_id": f"topcv_{_counter['n']}",
        "source": "topcv",
        "city": "Hà Nội",
        "work_mode": Job.WorkMode.ONSITE,
        "employment_type": Job.EmploymentType.FULL_TIME,
        "is_it": True,
        "deadline": timezone.localdate() + timedelta(days=days_left) if days_left is not None else None,
    }
    defaults.update(fields)
    job = Job.objects.create(title=title, company=Company.objects.get_or_create(name=company)[0], **defaults)
    job.skills.set([Skill.objects.get_or_create(name=s)[0] for s in skills])
    return job

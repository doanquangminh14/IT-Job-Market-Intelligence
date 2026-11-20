from django.contrib import admin

from .models import Company, Job, SavedJob, Skill


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "city", "work_mode", "salary_display", "deadline", "is_it", "source")
    list_filter = ("source", "is_it", "city", "work_mode", "employment_type")
    search_fields = ("title", "company__name", "job_id")
    autocomplete_fields = ("company",)
    filter_horizontal = ("skills",)
    date_hierarchy = "deadline"


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ("user", "job", "created_at")
    raw_id_fields = ("job",)

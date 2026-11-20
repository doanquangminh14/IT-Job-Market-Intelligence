from django.urls import path

from . import views

app_name = "jobs"

urlpatterns = [
    path("", views.job_list, name="list"),
    path("saved/", views.saved_jobs, name="saved"),
    path("<int:pk>/", views.job_detail, name="detail"),
    path("<int:pk>/save/", views.toggle_save, name="toggle_save"),
]

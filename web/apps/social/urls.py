from django.urls import path

from . import views

app_name = "community"

urlpatterns = [
    path("", views.feed, name="feed"),
    path("p/<int:pk>/", views.post_detail, name="post"),
    path("u/<str:username>/", views.profile, name="profile"),
]

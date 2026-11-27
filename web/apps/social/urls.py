from django.urls import path

from . import views

app_name = "community"

urlpatterns = [
    path("", views.feed, name="feed"),
    path("new/", views.create_post, name="create"),
    path("p/<int:pk>/", views.post_detail, name="post"),
    path("p/<int:pk>/comment/", views.add_comment, name="comment"),
    path("p/<int:pk>/like/", views.toggle_like, name="like"),
    path("p/<int:pk>/report/", views.report_post, name="report"),
    path("u/<str:username>/", views.profile, name="profile"),
    path("u/<str:username>/follow/", views.toggle_follow, name="follow"),
]

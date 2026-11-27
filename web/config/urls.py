from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "IT Job Market Intelligence"
admin.site.site_title = "IT Job Market Admin"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("jobs/", include("apps.jobs.urls")),
    path("analytics/", include("apps.analytics.urls")),
    path("community/", include("apps.social.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

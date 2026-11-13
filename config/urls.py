from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("projets/", include("projects.urls")),
    path("coups-de-main/", include("collabs.urls")),
    path("parcours/", include("paths.urls")),
    path("debats/", include("debates.urls")),
    path("", include("core.urls")),
]

if settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]

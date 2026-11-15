from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.static import serve

from core import views as core_views
from core.sitemaps import SITEMAPS

handler404 = "core.views.error_404"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("robots.txt", core_views.robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("favicon.ico", core_views.favicon_ico, name="favicon_ico"),
    path("site.webmanifest", core_views.webmanifest, name="webmanifest"),
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


from django.contrib.auth import get_user_model
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from collabs.models import HelpRequest
from debates.models import Debate
from paths.models import Path
from projects.models import Project

User = get_user_model()


class StaticViewSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return [
            "core:home",
            "projects:list",
            "collabs:list",
            "paths:list",
            "debates:list",
            "core:members",
            "core:privacy",
            "core:terms",
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        if item == "core:home":
            return 1.0
        if item == "projects:list":
            return 0.9
        if item in ("core:privacy", "core:terms"):
            return 0.4
        return 0.8


class ProjectSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Project.objects.order_by("-created")

    def lastmod(self, obj):
        return obj.created


class PathSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Path.objects.order_by("-created")

    def lastmod(self, obj):
        return obj.created


class HelpRequestSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        return HelpRequest.objects.order_by("-created")

    def lastmod(self, obj):
        return obj.created


class DebateSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Debate.objects.order_by("-created")

    def lastmod(self, obj):
        return obj.created


class MemberSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return User.objects.filter(is_active=True).order_by("-date_joined")

    def lastmod(self, obj):
        return obj.date_joined


SITEMAPS = {
    "pages": StaticViewSitemap,
    "projets": ProjectSitemap,
    "parcours": PathSitemap,
    "coups-de-main": HelpRequestSitemap,
    "debats": DebateSitemap,
    "membres": MemberSitemap,
}

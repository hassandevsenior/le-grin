import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from collabs.models import HelpRequest
from core.models import Tech
from debates.models import Debate
from debates.services import stance_context
from paths.models import Path
from projects.models import Project

User = get_user_model()
COOKIE_MAX_AGE = 60 * 60 * 24 * 180  # 6 mois


def home(request):
    debate = Debate.objects.filter(featured=True).first() or Debate.objects.first()
    context = {
        "projects": Project.objects.select_related("owner").annotate(
            pin_count=Count("pins", distinct=True), clap_count=Count("applause", distinct=True)
        ).order_by("-created")[:6],
        "help_requests": HelpRequest.objects.filter(is_open=True).select_related("author")[:3],
        "paths": Path.objects.select_related("author", "tech").annotate(step_count=Count("steps")).order_by("-created")[:3],
        "stats": {
            "members": User.objects.count(),
            "projects": Project.objects.count(),
            "paths": Path.objects.count(),
        },
        "debate": debate,
    }
    if debate:
        context.update(stance_context(request, debate))
    return render(request, "core/home.html", context)


def members(request):
    people = (
        User.objects.filter(is_active=True)
        .prefetch_related("techs")
        .annotate(
            project_count=Count("projects", distinct=True),
            kept=Count("commitments", filter=Q(commitments__status="kept"), distinct=True),
        )
        .order_by("-date_joined")
    )
    query = request.GET.get("q", "").strip()
    tech = request.GET.get("tech", "").strip()
    level = request.GET.get("niveau", "").strip()
    if query:
        people = people.filter(
            Q(username__icontains=query) | Q(bio__icontains=query) | Q(city__icontains=query)
        )
    if tech:
        people = people.filter(techs__slug=tech)
    if level in User.Level.values:
        people = people.filter(level=level)
    else:
        level = ""
    paginator = Paginator(people, 24)
    page = paginator.get_page(request.GET.get("page"))
    active_tech = Tech.objects.filter(slug=tech).first() if tech else None
    return render(
        request,
        "core/members.html",
        {
            "page": page,
            "total_count": paginator.count,
            "query": query,
            "tech": tech,
            "active_tech": active_tech,
            "level": level,
            "active_level_label": dict(User.Level.choices).get(level, ""),
            "has_filters": bool(query or tech or level),
            "levels": User.Level.choices,
            "techs": Tech.objects.annotate(n=Count("members")).filter(n__gt=0).order_by("-n")[:14],
        },
    )


@login_required
def notifications(request):
    items = list(request.user.notifications.all()[:40])
    request.user.notifications.filter(read=False).update(read=True)
    return render(request, "core/notifications.html", {"items": items})


def privacy(request):
    return render(request, "core/privacy.html")


def terms(request):
    return render(request, "core/terms.html")


@require_POST
def cookie_consent(request):
    choice = request.POST.get("choice", "essential")
    if choice not in ("accepted", "essential"):
        choice = "essential"

    wants_json = "application/json" in request.headers.get("Accept", "") or request.headers.get("X-Requested-With") == "fetch"
    if wants_json:
        response = JsonResponse({"choice": choice})
    else:
        target = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
        if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            target = "/"
        response = redirect(target)

    response.set_cookie(
        "grin_cookies",
        choice,
        max_age=COOKIE_MAX_AGE,
        samesite="Lax",
        secure=not settings.DEBUG,
        path="/",
    )
    return response


@require_GET
def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse("sitemap"))
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /notifications/",
        "Disallow: /compte/",
        "Disallow: /deconnexion/",
        "Disallow: /cookies/",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


@require_GET
def favicon_ico(request):
    ico_path = settings.BASE_DIR / "static" / "img" / "favicon.ico"
    response = HttpResponse(ico_path.read_bytes(), content_type="image/x-icon")
    response["Cache-Control"] = "public, max-age=2592000"
    return response


@require_GET
def webmanifest(request):
    payload = {
        "name": f"{settings.SITE_NAME} — Le coin des devs",
        "short_name": settings.SITE_NAME,
        "description": "Un grin pour les développeurs : montrer ses projets, recevoir des retours précis, apprendre étape par étape et s'entraider.",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f5f9ee",
        "theme_color": "#3a9f22",
        "lang": "fr",
        "icons": [
            {"src": static("img/favicon.svg"), "sizes": "any", "type": "image/svg+xml"},
            {"src": static("img/icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("img/icon-512.png"), "sizes": "512x512", "type": "image/png"},
        ],
    }
    response = HttpResponse(
        json.dumps(payload, ensure_ascii=False),
        content_type="application/manifest+json; charset=utf-8",
    )
    response["Cache-Control"] = "public, max-age=86400"
    return response


def error_404(request, exception=None):
    recent_projects = (
        Project.objects.select_related("owner")
        .annotate(pin_count=Count("pins", distinct=True), clap_count=Count("applause", distinct=True))
        .order_by("-created")[:3]
    )
    return render(request, "404.html", {"recent_projects": recent_projects}, status=404)


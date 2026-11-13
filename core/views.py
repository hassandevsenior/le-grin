from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render

from collabs.models import HelpRequest
from core.models import Tech
from debates.models import Debate
from debates.services import stance_context
from paths.models import Path
from projects.models import Project

User = get_user_model()


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
    tech = request.GET.get("tech", "")
    level = request.GET.get("niveau", "")
    if query:
        people = people.filter(
            Q(username__icontains=query) | Q(bio__icontains=query) | Q(city__icontains=query)
        )
    if tech:
        people = people.filter(techs__slug=tech)
    if level in User.Level.values:
        people = people.filter(level=level)
    page = Paginator(people, 24).get_page(request.GET.get("page"))
    return render(
        request,
        "core/members.html",
        {
            "page": page,
            "query": query,
            "tech": tech,
            "level": level,
            "levels": User.Level.choices,
            "techs": Tech.objects.annotate(n=Count("members")).filter(n__gt=0).order_by("-n")[:14],
        },
    )


@login_required
def notifications(request):
    items = list(request.user.notifications.all()[:40])
    request.user.notifications.filter(read=False).update(read=True)
    return render(request, "core/notifications.html", {"items": items})

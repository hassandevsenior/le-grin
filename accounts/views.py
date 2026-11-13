from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from debates.services import publish_pending

from .forms import ProfileForm, SignupForm

User = get_user_model()


def signup(request):
    if request.user.is_authenticated:
        return redirect("core:home")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        debate = publish_pending(request, user)
        login(request, user, backend="accounts.backends.EmailOrUsernameBackend")
        if debate:
            messages.success(request, "Bienvenue ! Ton vote est enregistré : dis-nous pourquoi.")
            return redirect(debate.get_absolute_url() + "#voter")
        messages.success(request, "Bienvenue au grin. Installe-toi.")
        return redirect("core:home")
    return render(request, "accounts/signup.html", {"form": form})


def profile(request, username):
    member = get_object_or_404(User.objects.prefetch_related("techs"), username=username)
    context = {
        "member": member,
        "projects": member.projects.annotate(
            pin_count=Count("pins", distinct=True), clap_count=Count("applause", distinct=True)
        ).order_by("-created"),
        "commitments": member.commitments.select_related("request")[:8],
        "stances": member.stances.exclude(text="").select_related("debate")[:3],
        "explanation_count": member.explanations.count(),
    }
    return render(request, "accounts/profile.html", context)


@login_required
def edit_profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profil mis à jour.")
        return redirect(request.user)
    return render(request, "accounts/edit.html", {"form": form})

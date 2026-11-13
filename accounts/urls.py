from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("inscription/", views.signup, name="signup"),
    path(
        "connexion/",
        auth_views.LoginView.as_view(template_name="accounts/login.html", redirect_authenticated_user=True),
        name="login",
    ),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
    path("compte/", views.edit_profile, name="edit"),
    path("@<str:username>/", views.profile, name="profile"),
]

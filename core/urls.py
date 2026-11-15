from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("membres/", views.members, name="members"),
    path("notifications/", views.notifications, name="notifications"),
    path("confidentialite/", views.privacy, name="privacy"),
    path("cgu/", views.terms, name="terms"),
    path("cookies/consentement/", views.cookie_consent, name="cookie_consent"),
]


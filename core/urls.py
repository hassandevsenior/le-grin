from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("membres/", views.members, name="members"),
    path("notifications/", views.notifications, name="notifications"),
]

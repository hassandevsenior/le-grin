from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class GrinUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Profil", {"fields": ("level", "bio", "city", "github", "techs")}),)
    list_display = ("username", "email", "level", "city", "date_joined")

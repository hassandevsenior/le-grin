from django.contrib import admin

from .models import Pin, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "stage", "created")
    search_fields = ("title", "tagline")


admin.site.register(Pin)

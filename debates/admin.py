from django.contrib import admin

from .models import Debate, Stance


@admin.register(Debate)
class DebateAdmin(admin.ModelAdmin):
    list_display = ("question", "featured", "created")
    prepopulated_fields = {"slug": ("question",)}


admin.site.register(Stance)

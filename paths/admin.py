from django.contrib import admin

from .models import Explanation, Path, Step

admin.site.register([Path, Step, Explanation])

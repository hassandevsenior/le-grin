from django.contrib import admin

from .models import Commitment, HelpRequest, Update

admin.site.register([HelpRequest, Commitment, Update])

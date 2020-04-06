from django.contrib import admin
from .models import *

class SlackUserInline(admin.TabularInline):
    model = SlackUser
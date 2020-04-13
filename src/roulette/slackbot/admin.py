from django.contrib import admin
from .models import *

class SlackUserInline(admin.TabularInline):
    model = SlackUser

class SlackAdminUserInline(admin.TabularInline):
    model = SlackAdminUser
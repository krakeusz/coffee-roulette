from django.contrib import auth
from django.test import TestCase


def create_natural_number_users(n_users):
    for i in range(1, n_users+1):
        auth.models.User.objects.create(
            username=str(i), email=str(i)+"@example.com")
    return auth.models.User.objects.all()

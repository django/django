from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered

from .models import Choice, Question

# We dinamically register/unregister the admin model in some tests
# This code is executed when tests are run, which may cause AlreadyRegistered exception
try:
    admin.site.register(Question)
    admin.site.register(Choice)
except AlreadyRegistered:
    pass

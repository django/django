"""
Test URLs for auth admins.
"""

from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.contrib.auth.urls import urlpatterns

# Create a silo'd admin site for just the user/group admins.
site = admin.AdminSite(name='auth_test_admin')
site.register(User, UserAdmin)
site.register(Group, GroupAdmin)

urlpatterns += [
    url(r'^admin/', site.urls),
]

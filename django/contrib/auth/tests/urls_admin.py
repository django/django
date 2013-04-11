"""
Test URLs for auth admins.
"""

from django.conf.urls import patterns, include
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
from django.contrib.auth.urls import urlpatterns

# Create a silo'd admin site for just the user/group admins.
site = admin.AdminSite(name='auth_test_admin')
site.register(User, UserAdmin)
site.register(Group, GroupAdmin)

urlpatterns = urlpatterns + patterns('',
    (r'^admin/', include(site.urls)),
)

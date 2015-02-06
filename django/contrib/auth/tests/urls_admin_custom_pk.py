"""
Test URLs for auth admins custom user pk.
"""

from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.contrib.auth.urls import urlpatterns


# Create a silo'd admin site for just the user/group admins.
site = admin.AdminSite(name='auth_test_admin_custom_pk')
site.register(get_user_model(), UserAdmin)

urlpatterns += [
    url(r'^admin/', include(site.urls)),
]

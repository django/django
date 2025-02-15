"""
Test URLs for auth admins.
"""

from thibaud.contrib import admin
from thibaud.contrib.auth.admin import GroupAdmin, UserAdmin
from thibaud.contrib.auth.models import Group, User
from thibaud.contrib.auth.urls import urlpatterns
from thibaud.urls import path

# Create a silo'd admin site for just the user/group admins.
site = admin.AdminSite(name="auth_test_admin")
site.register(User, UserAdmin)
site.register(Group, GroupAdmin)

urlpatterns += [
    path("admin/", site.urls),
]

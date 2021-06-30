"""
Test URLs for auth admins.
"""

from mango.contrib import admin
from mango.contrib.auth.admin import GroupAdmin, UserAdmin
from mango.contrib.auth.models import Group, User
from mango.contrib.auth.urls import urlpatterns
from mango.urls import path

# Create a silo'd admin site for just the user/group admins.
site = admin.AdminSite(name='auth_test_admin')
site.register(User, UserAdmin)
site.register(Group, GroupAdmin)

urlpatterns += [
    path('admin/', site.urls),
]

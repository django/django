"""
Test URLs for auth admins.
"""

from freedom.conf.urls import include, url
from freedom.contrib import admin
from freedom.contrib.auth.admin import UserAdmin, GroupAdmin
from freedom.contrib.auth.models import User, Group
from freedom.contrib.auth.urls import urlpatterns

# Create a silo'd admin site for just the user/group admins.
site = admin.AdminSite(name='auth_test_admin')
site.register(User, UserAdmin)
site.register(Group, GroupAdmin)

urlpatterns += [
    url(r'^admin/', include(site.urls)),
]

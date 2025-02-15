"""
A custom AdminSite for AdminViewPermissionsTest.test_login_has_permission().
"""

from thibaud.contrib import admin
from thibaud.contrib.auth import get_permission_codename
from thibaud.contrib.auth.forms import AuthenticationForm
from thibaud.core.exceptions import ValidationError

from . import admin as base_admin
from . import models

PERMISSION_NAME = "admin_views.%s" % get_permission_codename(
    "change", models.Article._meta
)


class PermissionAdminAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        if not user.is_active or not (user.is_staff or user.has_perm(PERMISSION_NAME)):
            raise ValidationError("permission denied")


class HasPermissionAdmin(admin.AdminSite):
    login_form = PermissionAdminAuthenticationForm

    def has_permission(self, request):
        return request.user.is_active and (
            request.user.is_staff or request.user.has_perm(PERMISSION_NAME)
        )


site = HasPermissionAdmin(name="has_permission_admin")
site.register(models.Article, base_admin.ArticleAdmin)

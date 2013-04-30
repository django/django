"""
A second, custom AdminSite -- see tests.CustomAdminSiteTests.
"""
from __future__ import absolute_import

from django.conf.urls import patterns
from django.contrib import admin
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from . import models, forms, admin as base_admin


class Admin2(admin.AdminSite):
    login_form = forms.CustomAdminAuthenticationForm
    login_template = 'custom_admin/login.html'
    logout_template = 'custom_admin/logout.html'
    index_template = ['custom_admin/index.html'] # a list, to test fix for #18697
    password_change_template = 'custom_admin/password_change_form.html'
    password_change_done_template = 'custom_admin/password_change_done.html'

    # A custom index view.
    def index(self, request, extra_context=None):
        return super(Admin2, self).index(request, {'foo': '*bar*'})

    def get_urls(self):
        return patterns('',
            (r'^my_view/$', self.admin_view(self.my_view)),
        ) + super(Admin2, self).get_urls()

    def my_view(self, request):
        return HttpResponse("Django is a magical pony!")


class UserLimitedAdmin(UserAdmin):
    # used for testing password change on a user not in queryset
    def get_queryset(self, request):
        qs = super(UserLimitedAdmin, self).get_queryset(request)
        return qs.filter(is_superuser=False)


class CustomPwdTemplateUserAdmin(UserAdmin):
    change_user_password_template = ['admin/auth/user/change_password.html'] # a list, to test fix for #18697


site = Admin2(name="admin2")

site.register(models.Article, base_admin.ArticleAdmin)
site.register(models.Section, inlines=[base_admin.ArticleInline])
site.register(models.Thing, base_admin.ThingAdmin)
site.register(models.Fabric, base_admin.FabricAdmin)
site.register(models.ChapterXtra1, base_admin.ChapterXtra1Admin)
site.register(User, UserLimitedAdmin)
site.register(models.UndeletableObject, base_admin.UndeletableObjectAdmin)
site.register(models.Simple, base_admin.AttributeErrorRaisingAdmin)

simple_site = Admin2(name='admin4')
simple_site.register(User, CustomPwdTemplateUserAdmin)

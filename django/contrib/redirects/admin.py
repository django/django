from django.apps import apps
from django.contrib import admin
from django.contrib.redirects.forms import RedirectForm
from django.contrib.redirects.models import Redirect
from django.utils.translation import gettext_lazy as _


@admin.register(Redirect)
class RedirectAdmin(admin.ModelAdmin):
    form = RedirectForm

    list_display = ('old_path', 'new_path', 'domain')
    list_filter = ('domain',)
    search_fields = ('domain', 'old_path', 'new_path')

    def get_fieldsets(self, request, obj=None):
        source_fields = ['old_path', 'domain']

        if apps.is_installed('django.contrib.sites'):
            source_fields.append('site')

        return (
            (_('Source'), {
                'fields': source_fields
            }),
            (_('Destination'), {
                'fields': ('new_path',)
            }),
        )

    def get_form(self, request, obj=None, **kwargs):
        kwargs['fields'] = ('old_path', 'domain', 'new_path')

        return super().get_form(request, obj, **kwargs)

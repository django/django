from django.contrib import admin
from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site


class RedirectAdmin(admin.ModelAdmin):
    list_display = ('old_path', 'new_path')
    search_fields = ('old_path', 'new_path')
    if Site._meta.installed:
        list_filter = ('site',)
        radio_fields = {'site': admin.VERTICAL}


admin.site.register(Redirect, RedirectAdmin)

from django.contrib import admin
from django.contrib.sites.models import Site


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('domain', 'name', 'urlconf')
    search_fields = ('domain', 'name', 'urlconf')

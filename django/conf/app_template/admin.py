# -*- coding: utf-8 -*-
"""
Admin interface for {{ app_name|title }} Django application.

.. seealso::
    http://docs.djangoproject.com/en/dev/ref/contrib/admin/
"""
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from {{ app_name }} import models


# Replace the following example with your admin interface or remove file.

class {{ app_name|title }}Admin(admin.ModelAdmin):
    """Admin interface for `{{ app_name|title }}` model."""

    list_display = ('name', 'category', 'date_modified')
    list_display_links = ('name',)

    date_hierarchy = 'date_modified'
    list_filter = ('category', 'user__username')
    search_fields = ('name', 'category', 'user__username')

admin.site.register(models.{{ app_name|title }}, {{ app_name|title }}Admin)


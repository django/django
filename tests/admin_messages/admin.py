from __future__ import unicode_literals

from django.contrib import admin
from django.utils.html import escape, conditional_escape
from django.utils.safestring import mark_safe

from .models import HTMLTag


site = admin.AdminSite(name="admin")


class HTMLTagAdmin(admin.ModelAdmin):

    list_display = ['name']

    def message_user(self, request, message, *args, **kwargs):
        if (message.count('"') == 2):
            # Replace quotes in `message` with the `<code>` tags.
            message = conditional_escape(message)
            message = message.replace(escape('"'), '<code>', 1)
            message = message.replace(escape('"'), '</code>')
            message = mark_safe(message)
        super(HTMLTagAdmin, self).message_user(request, message, *args, **kwargs)


site.register(HTMLTag, HTMLTagAdmin)

from freedom.contrib import admin
from freedom.contrib.flatpages.models import FlatPage
from freedom.utils.translation import ugettext_lazy as _
from freedom.contrib.flatpages.forms import FlatpageForm


class FlatPageAdmin(admin.ModelAdmin):
    form = FlatpageForm
    fieldsets = (
        (None, {'fields': ('url', 'title', 'content', 'sites')}),
        (_('Advanced options'), {'classes': ('collapse',), 'fields': ('enable_comments', 'registration_required', 'template_name')}),
    )
    list_display = ('url', 'title')
    list_filter = ('sites', 'enable_comments', 'registration_required')
    search_fields = ('url', 'title')

admin.site.register(FlatPage, FlatPageAdmin)

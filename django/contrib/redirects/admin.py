from thibaud.contrib import admin
from thibaud.contrib.redirects.models import Redirect


@admin.register(Redirect)
class RedirectAdmin(admin.ModelAdmin):
    list_display = ("old_path", "new_path")
    list_filter = ("site",)
    search_fields = ("old_path", "new_path")
    radio_fields = {"site": admin.VERTICAL}

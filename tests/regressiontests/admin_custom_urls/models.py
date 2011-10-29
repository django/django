from functools import update_wrapper

from django.contrib import admin
from django.db import models


class Action(models.Model):
    name = models.CharField(max_length=50, primary_key=True)
    description = models.CharField(max_length=70)

    def __unicode__(self):
        return self.name


class ActionAdmin(admin.ModelAdmin):
    """
    A ModelAdmin for the Action model that changes the URL of the add_view
    to '<app name>/<model name>/!add/'
    The Action model has a CharField PK.
    """

    list_display = ('name', 'description')

    def remove_url(self, name):
        """
        Remove all entries named 'name' from the ModelAdmin instance URL
        patterns list
        """
        return filter(lambda e: e.name != name, super(ActionAdmin, self).get_urls())

    def get_urls(self):
        # Add the URL of our custom 'add_view' view to the front of the URLs
        # list.  Remove the existing one(s) first
        from django.conf.urls import patterns, url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.module_name

        view_name = '%s_%s_add' % info

        return patterns('',
            url(r'^!add/$', wrap(self.add_view), name=view_name),
        ) + self.remove_url(view_name)


admin.site.register(Action, ActionAdmin)

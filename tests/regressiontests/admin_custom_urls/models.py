from functools import update_wrapper

from django.contrib import admin
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Action(models.Model):
    name = models.CharField(max_length=50, primary_key=True)
    description = models.CharField(max_length=70)

    def __str__(self):
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
        return [url for url in super(ActionAdmin, self).get_urls() if url.name != name]

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


class Person(models.Model):
    nick = models.CharField(max_length=20)


class PersonAdmin(admin.ModelAdmin):
    """A custom ModelAdmin that customizes the deprecated post_url_continue
    argument to response_add()"""
    def response_add(self, request, obj, post_url_continue='../%s/continue/',
                     continue_url=None, add_url=None, hasperm_url=None,
                     noperm_url=None):
        return super(PersonAdmin, self).response_add(request, obj,
                                                     post_url_continue,
                                                     continue_url, add_url,
                                                     hasperm_url, noperm_url)


admin.site.register(Person, PersonAdmin)


class City(models.Model):
    name = models.CharField(max_length=20)


class CityAdmin(admin.ModelAdmin):
    """A custom ModelAdmin that redirects to the changelist when the user
    presses the 'Save and add another' button when adding a model instance."""
    def response_add(self, request, obj,
                     add_another_url='admin:admin_custom_urls_city_changelist',
                     **kwargs):
        return super(CityAdmin, self).response_add(request, obj,
                                                   add_another_url=add_another_url,
                                                   **kwargs)


admin.site.register(City, CityAdmin)

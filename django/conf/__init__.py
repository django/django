"""
Settings and configuration for Django.

Values will be read from the module specified by the DJANGO_SETTINGS_MODULE environment
variable, and then from django.conf.global_settings; see the global settings file for
a list of all possible variables.
"""

import os
import sys
from django.conf import global_settings

ENVIRONMENT_VARIABLE = "DJANGO_SETTINGS_MODULE"

class LazySettings(object):
    """
    A lazy proxy for either global Django settings or a custom settings object.
    The user can manually configure settings prior to using them. Otherwise,
    Django uses the settings module pointed to by DJANGO_SETTINGS_MODULE.
    """
    def __init__(self):
        # _target must be either None or something that supports attribute
        # access (getattr, hasattr, etc).
        self._target = None

    def __getattr__(self, name):
        if self._target is None:
            self._import_settings()
        if name == '__members__':
            # Used to implement dir(obj), for example.
            return self._target.get_all_members()
        return getattr(self._target, name)

    def __setattr__(self, name, value):
        if name == '_target':
            # Assign directly to self.__dict__, because otherwise we'd call
            # __setattr__(), which would be an infinite loop.
            self.__dict__['_target'] = value
        else:
            setattr(self._target, name, value)

    def _import_settings(self):
        """
        Load the settings module pointed to by the environment variable. This
        is used the first time we need any settings at all, if the user has not
        previously configured the settings manually.
        """
        try:
            settings_module = os.environ[ENVIRONMENT_VARIABLE]
            if not settings_module: # If it's set but is an empty string.
                raise KeyError
        except KeyError:
            raise EnvironmentError, "Environment variable %s is undefined." % ENVIRONMENT_VARIABLE

        self._target = Settings(settings_module)

    def configure(self, default_settings=global_settings, **options):
        """
        Called to manually configure the settings. The 'default_settings'
        parameter sets where to retrieve any unspecified values from (its
        argument must support attribute access (__getattr__)).
        """
        if self._target != None:
            raise EnvironmentError, 'Settings already configured.'
        holder = UserSettingsHolder(default_settings)
        for name, value in options.items():
            setattr(holder, name, value)
        self._target = holder

class Settings(object):
    def __init__(self, settings_module):
        # update this dict from global settings (but only for ALL_CAPS settings)
        for setting in dir(global_settings):
            if setting == setting.upper():
                setattr(self, setting, getattr(global_settings, setting))

        # store the settings module in case someone later cares
        self.SETTINGS_MODULE = settings_module

        try:
            mod = __import__(self.SETTINGS_MODULE, '', '', [''])
        except ImportError, e:
            raise EnvironmentError, "Could not import settings '%s' (Is it on sys.path? Does it have syntax errors?): %s" % (self.SETTINGS_MODULE, e)

        # Settings that should be converted into tuples if they're mistakenly entered
        # as strings.
        tuple_settings = ("INSTALLED_APPS", "TEMPLATE_DIRS")

        for setting in dir(mod):
            if setting == setting.upper():
                setting_value = getattr(mod, setting)
                if setting in tuple_settings and type(setting_value) == str:
                    setting_value = (setting_value,) # In case the user forgot the comma.
                setattr(self, setting, setting_value)

        # Expand entries in INSTALLED_APPS like "django.contrib.*" to a list
        # of all those apps.
        new_installed_apps = []
        for app in self.INSTALLED_APPS:
            if app.endswith('.*'):
                appdir = os.path.dirname(__import__(app[:-2], '', '', ['']).__file__)
                for d in os.listdir(appdir):
                    if d.isalpha() and os.path.isdir(os.path.join(appdir, d)):
                        new_installed_apps.append('%s.%s' % (app[:-2], d))
            else:
                new_installed_apps.append(app)
        self.INSTALLED_APPS = new_installed_apps

        # move the time zone info into os.environ
        os.environ['TZ'] = self.TIME_ZONE

    def get_all_members(self):
        return dir(self)

class UserSettingsHolder(object):
    """
    Holder for user configured settings.
    """
    # SETTINGS_MODULE doesn't make much sense in the manually configured
    # (standalone) case.
    SETTINGS_MODULE = None

    def __init__(self, default_settings):
        """
        Requests for configuration variables not in this class are satisfied
        from the module specified in default_settings (if possible).
        """
        self.default_settings = default_settings

    def __getattr__(self, name):
        return getattr(self.default_settings, name)

    def get_all_members(self):
        return dir(self) + dir(self.default_settings)

settings = LazySettings()

# This function replaces itself with django.utils.translation.gettext() the
# first time it's run. This is necessary because the import of
# django.utils.translation requires a working settings module, and loading it
# from within this file would cause a circular import.
def first_time_gettext(*args):
    from django.utils.translation import gettext
    __builtins__['_'] = gettext
    return gettext(*args)

__builtins__['_'] = first_time_gettext

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

class Settings:

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
            raise EnvironmentError, "Could not import settings '%s' (is it on sys.path?): %s" % (self.SETTINGS_MODULE, e)

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

# try to load DJANGO_SETTINGS_MODULE
try:
    settings_module = os.environ[ENVIRONMENT_VARIABLE]
    if not settings_module: # If it's set but is an empty string.
        raise KeyError
except KeyError:
    raise EnvironmentError, "Environment variable %s is undefined." % ENVIRONMENT_VARIABLE

# instantiate the configuration object
settings = Settings(settings_module)

# install the translation machinery so that it is available
from django.utils import translation
translation.install()


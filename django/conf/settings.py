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

# get a reference to this module (why isn't there a __module__ magic var?)
me = sys.modules[__name__]

# update this dict from global settings (but only for ALL_CAPS settings)
for setting in dir(global_settings):
    if setting == setting.upper():
        setattr(me, setting, getattr(global_settings, setting))

# try to load DJANGO_SETTINGS_MODULE
try:
    me.SETTINGS_MODULE = os.environ[ENVIRONMENT_VARIABLE]
    if not me.SETTINGS_MODULE: # If it's set but is an empty string.
        raise KeyError
except KeyError:
    raise EnvironmentError, "Environment variable %s is undefined." % ENVIRONMENT_VARIABLE

try:
    mod = __import__(me.SETTINGS_MODULE, '', '', [''])
except ImportError, e:
    raise EnvironmentError, "Could not import %s '%s' (is it on sys.path?): %s" % (ENVIRONMENT_VARIABLE, me.SETTINGS_MODULE, e)

# Settings that should be converted into tuples if they're mistakenly entered
# as strings.
tuple_settings = ("INSTALLED_APPS", "TEMPLATE_DIRS")

for setting in dir(mod):
    if setting == setting.upper():
        setting_value = getattr(mod, setting)
        if setting in tuple_settings and type(setting_value) == str:
            setting_value = (setting_value,) # In case the user forgot the comma.
        setattr(me, setting, setting_value)

# save DJANGO_SETTINGS_MODULE in case anyone in the future cares
me.SETTINGS_MODULE = os.environ.get(ENVIRONMENT_VARIABLE, '')

# move the time zone info into os.environ
os.environ['TZ'] = me.TIME_ZONE

# finally, clean up my namespace
for k in dir(me):
    if not k.startswith('_') and k != 'me' and k != k.upper():
        delattr(me, k)
del me, k

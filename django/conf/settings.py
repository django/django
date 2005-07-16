"""
Settings and configuration for Django.

Values will be read from the module specified by the DJANGO_SETTINGS_MODULE environment
variable, and then from django.conf.global_settings; see the global settings file for 
a list of all possible variables.
"""

import os
import sys
from django.conf import global_settings

# get a reference to this module (why isn't there a __module__ magic var?) 
me = sys.modules[__name__]

# update this dict from global settings (but only for ALL_CAPS settings)
for setting in dir(global_settings):
    if setting == setting.upper():
        setattr(me, setting, getattr(global_settings, setting))

# try to load DJANGO_SETTINGS_MODULE
try:
    me.SETTINGS_MODULE = os.environ["DJANGO_SETTINGS_MODULE"]
except KeyError:
    raise EnvironmentError, "Environemnt variable DJANGO_SETTINGS_MODULE is undefined."

try:
    mod = __import__(me.SETTINGS_MODULE, '', '', [''])
except ImportError, e:
    raise EnvironmentError, "Could not import DJANGO_SETTINGS_MODULE '%s' (is it on sys.path?): %s" % (me.SETTINGS_MODULE, e)

for setting in dir(mod):
    if setting == setting.upper():
        setattr(me, setting, getattr(mod, setting))

# save DJANGO_SETTINGS_MODULE in case anyone in the future cares
me.SETTINGS_MODULE = os.environ.get('DJANGO_SETTINGS_MODULE', '')
    
# move the time zone info into os.environ
os.environ['TZ'] = me.TIME_ZONE

# finally, clean up my namespace
for k in dir(me):
    if not k.startswith('_') and k != 'me' and k != k.upper():
        delattr(me, k)
del me, k


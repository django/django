# This module is DEPRECATED!
#
# You should no longer be pointing your mod_python configuration
# at "django.core.handler".
#
# Use "django.core.handlers.modpython" instead.

from django.core.handlers.modpython import ModPythonHandler

def handler(req):
    return ModPythonHandler()(req)

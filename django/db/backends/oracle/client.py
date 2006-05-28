from django.conf import settings
import os

def runshell():
    args = ''
    args += settings.DATABASE_USER
    if settings.DATABASE_PASSWORD:
        args += "/%s" % settings.DATABASE_PASSWORD
    args += "@%s" % settings.DATABASE_NAME
    os.execvp('sqlplus', args)

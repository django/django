from django.conf import settings
import os

def runshell():
    args = ['']
    args += ["-U%s" % settings.DATABASE_USER]
    if settings.DATABASE_PASSWORD:
        args += ["-W"]
    if settings.DATABASE_HOST:
        args += ["-h %s" % settings.DATABASE_HOST]
    if settings.DATABASE_PORT:
        args += ["-p %s" % settings.DATABASE_PORT]
    args += [settings.DATABASE_NAME]
    os.execvp('psql', args)

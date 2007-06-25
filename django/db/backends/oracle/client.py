from django.conf import settings
import os

def runshell():
    dsn = settings.DATABASE_USER
    if settings.DATABASE_PASSWORD:
        dsn += "/%s" % settings.DATABASE_PASSWORD
    if settings.DATABASE_NAME:
        dsn += "@%s" % settings.DATABASE_NAME
    args = ["sqlplus", "-L", dsn]
    os.execvp("sqlplus", args)

from django.conf import settings
import os

def runshell():
    args = ['psql']
    if settings.DATABASE_USER:
        args += ["-U", settings.DATABASE_USER]
    if settings.DATABASE_PASSWORD:
        args += ["-W"]
    if settings.DATABASE_HOST:
        args.extend(["-h", settings.DATABASE_HOST])
    if settings.DATABASE_PORT:
        args.extend(["-p", str(settings.DATABASE_PORT)])
    args += [settings.DATABASE_NAME]
    os.execvp('psql', args)

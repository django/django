import os

def runshell(settings):
    args = ['']
    args += ["--user=%s" % settings.DATABASE_USER]
    if settings.DATABASE_PASSWORD:
        args += ["--password=%s" % settings.DATABASE_PASSWORD]
    if settings.DATABASE_HOST:
        args += ["--host=%s" % settings.DATABASE_HOST]
    if settings.DATABASE_PORT:
        args += ["--port=%s" % settings.DATABASE_PORT]
    args += [settings.DATABASE_NAME]
    os.execvp('mysql', args)

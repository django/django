import os

def runshell(settings):
    args = ''
    args += settings.DATABASE_USER
    if settings.DATABASE_PASSWORD:
        args += "/%s" % settings.DATABASE_PASSWORD
    args += "@%s" % settings.DATABASE_NAME
    os.execvp('sqlplus', args)

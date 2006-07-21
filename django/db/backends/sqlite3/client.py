import os

def runshell(settings):
    args = ['', settings.DATABASE_NAME]
    os.execvp('sqlite3', args)

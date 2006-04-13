from django.conf import settings
import os

def runshell():
    args = ['', settings.DATABASE_NAME]
    os.execvp('sqlite3', args)

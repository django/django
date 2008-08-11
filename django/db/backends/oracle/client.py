from django.db.backends import BaseDatabaseClient
from django.conf import settings
import os

class DatabaseClient(BaseDatabaseClient):
    def runshell(self):
        dsn = settings.DATABASE_USER
        if settings.DATABASE_PASSWORD:
            dsn += "/%s" % settings.DATABASE_PASSWORD
        if settings.DATABASE_NAME:
            dsn += "@%s" % settings.DATABASE_NAME
        args = ["sqlplus", "-L", dsn]
        os.execvp("sqlplus", args)

from django.db.backends import BaseDatabaseClient
from django.conf import settings
import os

class DatabaseClient(BaseDatabaseClient):
    def runshell(self):
        args = ['', settings.DATABASE_NAME]
        os.execvp('sqlite3', args)

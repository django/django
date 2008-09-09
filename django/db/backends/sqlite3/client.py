from django.db.backends import BaseDatabaseClient
from django.conf import settings
import os

class DatabaseClient(BaseDatabaseClient):
    executable_name = 'sqlite3'

    def runshell(self):
        args = ['', settings.DATABASE_NAME]
        os.execvp(self.executable_name, args)

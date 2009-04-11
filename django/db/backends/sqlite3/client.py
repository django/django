from django.db.backends import BaseDatabaseClient
from django.conf import settings
import os
import sys

class DatabaseClient(BaseDatabaseClient):
    executable_name = 'sqlite3'

    def runshell(self):
        args = [self.executable_name, settings.DATABASE_NAME]
        if os.name == 'nt':
            sys.exit(os.system(" ".join(args)))
        else:
            os.execvp(self.executable_name, args)

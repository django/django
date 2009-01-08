from django.db.backends import BaseDatabaseClient
from django.conf import settings
import os

class DatabaseClient(BaseDatabaseClient):
    executable_name = 'sqlplus'

    def runshell(self):
        from django.db import connection
        conn_string = connection._connect_string(settings)
        args = [self.executable_name, "-L", conn_string]
        os.execvp(self.executable_name, args)

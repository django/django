import os
import sys

from django.db.backends import BaseDatabaseClient


class DatabaseClient(BaseDatabaseClient):
    executable_name = 'sqlplus'

    def runshell(self):
        conn_string = self.connection._connect_string()
        args = [self.executable_name, "-L", conn_string]
        if os.name == 'nt':
            sys.exit(os.system(" ".join(args)))
        else:
            os.execvp(self.executable_name, args)

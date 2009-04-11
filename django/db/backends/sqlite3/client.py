import os
import sys

from django.db.backends import BaseDatabaseClient

class DatabaseClient(BaseDatabaseClient):
    executable_name = 'sqlite3'

    def runshell(self):
        args = [self.executable_name,
                self.connection.settings_dict['DATABASE_NAME']]
        if os.name == 'nt':
            sys.exit(os.system(" ".join(args)))
        else:
            os.execvp(self.executable_name, args)


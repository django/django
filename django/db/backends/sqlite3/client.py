import subprocess

from django.db.backends import BaseDatabaseClient


class DatabaseClient(BaseDatabaseClient):
    executable_name = 'sqlite3'

    def runshell(self):
        args = [self.executable_name,
                self.connection.settings_dict['NAME']]
        subprocess.call(args)

from django.db.backends import BaseDatabaseClient
import os

class DatabaseClient(BaseDatabaseClient):
    executable_name = 'sqlite3'

    def runshell(self):
        args = ['', self.connection.settings_dict['DATABASE_NAME']]
        os.execvp(self.executable_name, args)

from django.db.backends import BaseDatabaseClient
import os

class DatabaseClient(BaseDatabaseClient):
    executable_name = 'sqlplus'

    def runshell(self):
        conn_string = self.connection._connect_string()
        args = [self.executable_name, "-L", conn_string]
        os.execvp(self.executable_name, args)

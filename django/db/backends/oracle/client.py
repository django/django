import shutil
import subprocess

from django.db.backends.base.client import BaseDatabaseClient


class DatabaseClient(BaseDatabaseClient):
    executable_name = 'sqlplus'
    wrapper_name = 'rlwrap'

    def runshell(self):
        conn_string = self.connection._connect_string()
        args = [self.executable_name, "-L", conn_string]
        wrapper_path = shutil.which(self.wrapper_name)
        if wrapper_path:
            args = [wrapper_path, *args]
        subprocess.check_call(args)

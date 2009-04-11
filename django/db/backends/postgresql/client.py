import os
import sys

from django.db.backends import BaseDatabaseClient

class DatabaseClient(BaseDatabaseClient):
    executable_name = 'psql'

    def runshell(self):
        settings_dict = self.connection.settings_dict
        args = [self.executable_name]
        if settings_dict['DATABASE_USER']:
            args += ["-U", settings_dict['DATABASE_USER']]
        if settings_dict['DATABASE_HOST']:
            args.extend(["-h", settings_dict['DATABASE_HOST']])
        if settings_dict['DATABASE_PORT']:
            args.extend(["-p", str(settings_dict['DATABASE_PORT'])])
        args += [settings_dict['DATABASE_NAME']]
        if os.name == 'nt':
            sys.exit(os.system(" ".join(args)))
        else:
            os.execvp(self.executable_name, args)


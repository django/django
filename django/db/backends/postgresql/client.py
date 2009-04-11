from django.db.backends import BaseDatabaseClient
from django.conf import settings
import os
import sys

class DatabaseClient(BaseDatabaseClient):
    executable_name = 'psql'

    def runshell(self):
        args = [self.executable_name]
        if settings.DATABASE_USER:
            args += ["-U", settings.DATABASE_USER]
        if settings.DATABASE_HOST:
            args.extend(["-h", settings.DATABASE_HOST])
        if settings.DATABASE_PORT:
            args.extend(["-p", str(settings.DATABASE_PORT)])
        args += [settings.DATABASE_NAME]
        if os.name == 'nt':
            sys.exit(os.system(" ".join(args)))
        else:
            os.execvp(self.executable_name, args)

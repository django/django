from django.db.backends import BaseDatabaseClient
from django.conf import settings
import os

class DatabaseClient(BaseDatabaseClient):
    def runshell(self):
        args = ['']
        db = settings.DATABASE_OPTIONS.get('db', settings.DATABASE_NAME)
        user = settings.DATABASE_OPTIONS.get('user', settings.DATABASE_USER)
        passwd = settings.DATABASE_OPTIONS.get('passwd', settings.DATABASE_PASSWORD)
        host = settings.DATABASE_OPTIONS.get('host', settings.DATABASE_HOST)
        port = settings.DATABASE_OPTIONS.get('port', settings.DATABASE_PORT)
        defaults_file = settings.DATABASE_OPTIONS.get('read_default_file')
        # Seems to be no good way to set sql_mode with CLI
    
        if defaults_file:
            args += ["--defaults-file=%s" % defaults_file]
        if user:
            args += ["--user=%s" % user]
        if passwd:
            args += ["--password=%s" % passwd]
        if host:
            args += ["--host=%s" % host]
        if port:
            args += ["--port=%s" % port]
        if db:
            args += [db]

        os.execvp('mysql', args)

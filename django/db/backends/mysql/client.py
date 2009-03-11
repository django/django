from django.db.backends import BaseDatabaseClient
import os

class DatabaseClient(BaseDatabaseClient):
    executable_name = 'mysql'

    def runshell(self):
        settings_dict = self.connection.settings_dict
        args = ['']
        db = settings_dict['DATABASE_OPTIONS'].get('db', settings_dict['DATABASE_NAME'])
        user = settings_dict['DATABASE_OPTIONS'].get('user', settings_dict['DATABASE_USER'])
        passwd = settings_dict['DATABASE_OPTIONS'].get('passwd', settings_dict['DATABASE_PASSWORD'])
        host = settings_dict['DATABASE_OPTIONS'].get('host', settings_dict['DATABASE_HOST'])
        port = settings_dict['DATABASE_OPTIONS'].get('port', settings_dict['DATABASE_PORT'])
        defaults_file = settings_dict['DATABASE_OPTIONS'].get('read_default_file')
        # Seems to be no good way to set sql_mode with CLI.
    
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

        os.execvp(self.executable_name, args)

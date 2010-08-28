import os
import sys

from django.db.backends import BaseDatabaseClient

class DatabaseClient(BaseDatabaseClient):
    executable_name = 'mysql'

    def runshell(self):
        settings_dict = self.connection.settings_dict
        args = [self.executable_name]
        db = settings_dict['OPTIONS'].get('db', settings_dict['NAME'])
        user = settings_dict['OPTIONS'].get('user', settings_dict['USER'])
        passwd = settings_dict['OPTIONS'].get('passwd', settings_dict['PASSWORD'])
        host = settings_dict['OPTIONS'].get('host', settings_dict['HOST'])
        port = settings_dict['OPTIONS'].get('port', settings_dict['PORT'])
        defaults_file = settings_dict['OPTIONS'].get('read_default_file')
        # Seems to be no good way to set sql_mode with CLI.

        if defaults_file:
            args += ["--defaults-file=%s" % defaults_file]
        if user:
            args += ["--user=%s" % user]
        if passwd:
            args += ["--password=%s" % passwd]
        if host:
            if '/' in host:
                args += ["--socket=%s" % host]
            else:
             	args += ["--host=%s" % host]
        if port:
            args += ["--port=%s" % port]
        if db:
            args += [db]

        if os.name == 'nt':
            sys.exit(os.system(" ".join(args)))
        else:
            os.execvp(self.executable_name, args)


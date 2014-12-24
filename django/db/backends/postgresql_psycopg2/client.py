import os
import subprocess

from django.db.backends import BaseDatabaseClient


class DatabaseClient(BaseDatabaseClient):
    executable_name = 'psql'

    @classmethod
    def settings_to_cmd_args(cls, settings_dict):
        args = [cls.executable_name]
        if settings_dict['USER']:
            args += ["-U", settings_dict['USER']]
        if settings_dict['HOST']:
            args.extend(["-h", settings_dict['HOST']])
        if settings_dict['PORT']:
            args.extend(["-p", str(settings_dict['PORT'])])
        args += [settings_dict['NAME']]

        if settings_dict['OPTIONS']:
            flags = ['='.join(map(str, i)) for i in settings_dict['OPTIONS'].items()]
            option_line = ' '.join(flags)
            os.environ['PGOPTIONS'] = '-c %s' % option_line

        return args

    def runshell(self):
        args = DatabaseClient.settings_to_cmd_args(self.connection.settings_dict)
        subprocess.call(args)

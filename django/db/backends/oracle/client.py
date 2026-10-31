import shutil
import subprocess

from django.db.backends.base.client import BaseDatabaseClient


class DatabaseClient(BaseDatabaseClient):
    executable_name = "sqlplus"
    wrapper_name = "rlwrap"

    @staticmethod
    def connect_string(settings_dict):
        from django.db.backends.oracle.utils import dsn

        return '%s/"%s"@%s' % (
            settings_dict["USER"],
            settings_dict["PASSWORD"],
            dsn(settings_dict),
        )

    @classmethod
    def settings_to_cmd_args_env(cls, settings_dict, parameters):
        args = [cls.executable_name, "-L", cls.connect_string(settings_dict)]
        wrapper_path = shutil.which(cls.wrapper_name)
        if wrapper_path:
            args = [wrapper_path, *args]
        args.extend(parameters)
        return args, None

    def runshell(self, parameters):
        try:
            super().runshell(parameters)
        except subprocess.CalledProcessError as exc:
            # SQL*Plus arguments contain credentials; omit them.
            exc.cmd = [self.executable_name]
            raise

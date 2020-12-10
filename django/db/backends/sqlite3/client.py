from django.db.backends.base.client import BaseDatabaseClient


class DatabaseClient(BaseDatabaseClient):
    executable_name = 'sqlite3'

    @classmethod
    def settings_to_cmd_args_env(cls, settings_dict, parameters):
        args = [
            cls.executable_name,
            # TODO: Remove str() when dropping support for PY37. args
            # parameter accepts path-like objects on Windows since Python 3.8.
            str(settings_dict['NAME']),
            *parameters,
        ]
        return args, None

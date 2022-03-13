from django.db.backends.base.client import BaseAsyncDatabaseClient


class DatabaseClient(BaseAsyncDatabaseClient):
    executable_name = "sqlite3"

    @classmethod
    def settings_to_cmd_args_env(cls, settings_dict, parameters):
        args = [cls.executable_name, settings_dict["NAME"], *parameters]
        return args, None

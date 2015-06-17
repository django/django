import os
import subprocess

from django.core.files.temp import NamedTemporaryFile
from django.db.backends.base.client import BaseDatabaseClient
from django.utils.six import print_


def _escape_pgpass(txt):
    """
    Escape a fragment of a PostgreSQL .pgpass file.
    """
    return txt.replace('\\', '\\\\').replace(':', '\\:')


class DatabaseClient(BaseDatabaseClient):
    executable_name = 'psql'

    @classmethod
    def runshell_db(cls, settings_dict):
        args = [cls.executable_name]

        host = settings_dict.get('HOST', '')
        port = settings_dict.get('PORT', '')
        name = settings_dict.get('NAME', '')
        user = settings_dict.get('USER', '')
        passwd = settings_dict.get('PASSWORD', '')

        if user:
            args += ['-U', user]
        if host:
            args += ['-h', host]
        if port:
            args += ['-p', str(port)]
        args += [name]

        temp_pgpass = None
        try:
            if passwd:
                # Create temporary .pgpass file.
                temp_pgpass = NamedTemporaryFile(mode='w+')
                try:
                    print_(
                        _escape_pgpass(host) or '*',
                        str(port) or '*',
                        _escape_pgpass(name) or '*',
                        _escape_pgpass(user) or '*',
                        _escape_pgpass(passwd),
                        file=temp_pgpass,
                        sep=':',
                        flush=True,
                    )
                    os.environ['PGPASSFILE'] = temp_pgpass.name
                except UnicodeEncodeError:
                    # If the current locale can't encode the data, we let
                    # the user input the password manually.
                    pass
            subprocess.call(args)
        finally:
            if temp_pgpass:
                temp_pgpass.close()
                if 'PGPASSFILE' in os.environ:  # unit tests need cleanup
                    del os.environ['PGPASSFILE']

    def runshell(self):
        DatabaseClient.runshell_db(self.connection.settings_dict)

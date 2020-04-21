import subprocess

from django.db.backends.base.client import BaseDatabaseClient


class DatabaseClient(BaseDatabaseClient):
    executable_name = 'mysql'

    @classmethod
    def settings_to_cmd_args(cls, settings_dict, parameters):
        args = [cls.executable_name]
        conn_params = {**settings_dict, **settings_dict['OPTIONS']}
        db = conn_params.get('db', '')
        user = conn_params.get('user', '')
        passwd = conn_params.get('password', '')
        host = conn_params.get('host', '')
        port = conn_params.get('port', '')
        server_ca = conn_params.get('ssl', {}).get('ca')
        client_cert = conn_params.get('ssl', {}).get('cert')
        client_key = conn_params.get('ssl', {}).get('key')
        defaults_file = conn_params.get('read_default_file')
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
        if server_ca:
            args += ["--ssl-ca=%s" % server_ca]
        if client_cert:
            args += ["--ssl-cert=%s" % client_cert]
        if client_key:
            args += ["--ssl-key=%s" % client_key]
        if db:
            args += [db]
        args.extend(parameters)
        return args

    def runshell(self, parameters):
        args = DatabaseClient.settings_to_cmd_args(self.connection.settings_dict, parameters)
        subprocess.run(args, check=True)

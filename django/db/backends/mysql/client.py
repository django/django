import subprocess

from django.db.backends.base.client import BaseDatabaseClient


class DatabaseClient(BaseDatabaseClient):
    executable_name = 'mysql'

    # Executable name for recent versions of MySQL, add
    # 'MYSQL_VERSION' : 8 to settings.py for this to take effect
    executable_name_mysql8 = 'mysqlsh'

    @classmethod
    def settings_to_cmd_args(cls, settings_dict):
        args = [cls.executable_name]
        db = settings_dict['OPTIONS'].get('db', settings_dict['NAME'])
        user = settings_dict['OPTIONS'].get('user', settings_dict['USER'])
        passwd = settings_dict['OPTIONS'].get('passwd', settings_dict['PASSWORD'])
        host = settings_dict['OPTIONS'].get('host', settings_dict['HOST'])
        port = settings_dict['OPTIONS'].get('port', settings_dict['PORT'])
        server_ca = settings_dict['OPTIONS'].get('ssl', {}).get('ca')
        client_cert = settings_dict['OPTIONS'].get('ssl', {}).get('cert')
        client_key = settings_dict['OPTIONS'].get('ssl', {}).get('key')
        defaults_file = settings_dict['OPTIONS'].get('read_default_file')
        # Seems to be no good way to set sql_mode with CLI.

        # This controls the executable name and other options with the
        # latest version of mysql shell v = 8.x+
        mysql_version = settings_dict['OPTIONS'].get('version', settings_dict['MYSQL_VERSION'])

        # Additional options to use in settings.py
        # Most people are probably familiar with MySQL's classic session,
        # but others may like to use JS or Python sessions in the
        # mysql shell
        sql_classic_session = None
        if 'SQL_CLASSIC_SESSION' in settings_dict.keys():
            sql_classic_session = settings_dict['OPTIONS'].get('sql_classic_session', settings_dict['SQL_CLASSIC_SESSION'])
        sql_javascript_session = None
        if 'SQL_JAVASCRIPT_SESSION' in settings_dict.keys():
            sql_javascript_session = settings_dict['OPTIONS'].get('sql_javascript_session', settings_dict['SQL_JAVASCRIPT_SESSION'])
        sql_python_session = None
        if 'SQL_PYTHON_SESSION' in settings_dict:
            sql_python_session = settings_dict['OPTIONS'].get('sql_python_session', settings_dict['SQL_PYTHON_SESSION'])
        
        if mysql_version == 8:
            args = [cls.executable_name_mysql8]
        else:
            args = [cls.executable_name]

        if defaults_file:
            args += ["--defaults-file=%s" % defaults_file]
        if user:
            args += ["--user=%s" % user]
        if passwd:
            args += ["--password=%s" % passwd]
        if host:
            # fixme for [URI] option on mysqlsh command line
            if '/' in host:
                args += ["--socket=%s" % host]
            else:
                # The host in latest MySQL shell actually doesn't
                # need this; just put the hostname or IP right on
                # the end as the last argument (rather than the)
                # old way of the last argument being the database/
                # schema without any --opt= prefix
                args += ["%s" % host]
        if port:
            args += ["--port=%s" % port]
        if server_ca:
            args += ["--ssl-ca=%s" % server_ca]
        if client_cert:
            args += ["--ssl-cert=%s" % client_cert]
        if client_key:
            args += ["--ssl-key=%s" % client_key]
        if db:
            # --schema and --database the same, MySql and MySql Shell 8
            args += ["--schema=%s" % db] 
        if sql_classic_session:
            args += ["%s" % "--sqlc"]
        if sql_javascript_session:
            args += ["%s" % "--javascript"] 
        if sql_python_session:
            args += ["%s" % "--python"]
        return args

    def runshell(self):
        args = DatabaseClient.settings_to_cmd_args(self.connection.settings_dict)
        subprocess.run(args, check=True)

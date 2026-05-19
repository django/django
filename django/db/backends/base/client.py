import os
import signal
import subprocess


class BaseDatabaseClient:
    """Encapsulate backend-specific methods for opening a client shell."""

    # This should be a string representing the name of the executable
    # (e.g., "psql"). Subclasses must override this.
    executable_name = None

    def __init__(self, connection):
        # connection is an instance of BaseDatabaseWrapper.
        self.connection = connection

    def __del__(self):
        del self.connection

    @classmethod
    def settings_to_cmd_args_env(cls, settings_dict, parameters):
        raise NotImplementedError(
            "subclasses of BaseDatabaseClient must provide a "
            "settings_to_cmd_args_env() method or override a runshell()."
        )

    def runshell(self, parameters):
        args, env = self.settings_to_cmd_args_env(
            self.connection.settings_dict, parameters
        )
        env = {**os.environ, **env} if env else None
        sigint_handler = None
        if hasattr(signal, "SIGINT"):
            try:
                sigint_handler = signal.getsignal(signal.SIGINT)
            except ValueError:
                pass
        try:
            if sigint_handler is not None:
                signal.signal(signal.SIGINT, signal.SIG_IGN)
            subprocess.run(args, env=env, check=True)
        finally:
            if sigint_handler is not None:
                try:
                    signal.signal(signal.SIGINT, sigint_handler)
                except ValueError:
                    pass

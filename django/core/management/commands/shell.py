import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Runs a Python interactive interpreter. Tries to use IPython or bpython, if one of them is available."
    requires_system_checks = False
    shells = ['ipython', 'bpython']

    def add_arguments(self, parser):
        parser.add_argument('--plain', action='store_true', dest='plain',
            help='Tells Django to use plain Python, not IPython or bpython.')
        parser.add_argument('--no-startup', action='store_true', dest='no_startup',
            help='When using plain Python, ignore the PYTHONSTARTUP environment variable and ~/.pythonrc.py script.')
        parser.add_argument('-i', '--interface', choices=self.shells, dest='interface',
            help='Specify an interactive interpreter interface. Available options: "ipython" and "bpython"')

    def _ipython_pre_011(self):
        """Start IPython pre-0.11"""
        from IPython.Shell import IPShell
        shell = IPShell(argv=[])
        shell.mainloop()

    def _ipython_pre_100(self):
        """Start IPython pre-1.0.0"""
        from IPython.frontend.terminal.ipapp import TerminalIPythonApp
        app = TerminalIPythonApp.instance()
        app.initialize(argv=[])
        app.start()

    def _ipython(self):
        """Start IPython >= 1.0"""
        from IPython import start_ipython
        start_ipython(argv=[])

    def ipython(self):
        """Start any version of IPython"""
        for ip in (self._ipython, self._ipython_pre_100, self._ipython_pre_011):
            try:
                ip()
            except ImportError:
                pass
            else:
                return
        # no IPython, raise ImportError
        raise ImportError("No IPython")

    def bpython(self):
        import bpython
        bpython.embed()

    def run_shell(self, shell=None):
        available_shells = [shell] if shell else self.shells

        for shell in available_shells:
            try:
                return getattr(self, shell)()
            except ImportError:
                pass
        raise ImportError

    def handle(self, **options):
        try:
            if options['plain']:
                # Don't bother loading IPython, because the user wants plain Python.
                raise ImportError

            self.run_shell(shell=options['interface'])
        except ImportError:
            import code
            # Set up a dictionary to serve as the environment for the shell, so
            # that tab completion works on objects that are imported at runtime.
            # See ticket 5082.
            imported_objects = {}
            try:  # Try activating rlcompleter, because it's handy.
                import readline
            except ImportError:
                pass
            else:
                # We don't have to wrap the following import in a 'try', because
                # we already know 'readline' was imported successfully.
                import rlcompleter
                readline.set_completer(rlcompleter.Completer(imported_objects).complete)
                readline.parse_and_bind("tab:complete")

            # We want to honor both $PYTHONSTARTUP and .pythonrc.py, so follow system
            # conventions and get $PYTHONSTARTUP first then .pythonrc.py.
            if not options['no_startup']:
                for pythonrc in (os.environ.get("PYTHONSTARTUP"), '~/.pythonrc.py'):
                    if not pythonrc:
                        continue
                    pythonrc = os.path.expanduser(pythonrc)
                    if not os.path.isfile(pythonrc):
                        continue
                    try:
                        with open(pythonrc) as handle:
                            exec(compile(handle.read(), pythonrc, 'exec'), imported_objects)
                    except NameError:
                        pass
            code.interact(local=imported_objects)

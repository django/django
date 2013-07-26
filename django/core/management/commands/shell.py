import os
from django.core.management.base import NoArgsCommand
from optparse import make_option


class Command(NoArgsCommand):
    shells = ['ipython', 'bpython']

    option_list = NoArgsCommand.option_list + (
        make_option('--plain', action='store_true', dest='plain',
            help='Tells Django to use plain Python, not IPython or bpython.'),
        make_option('--no-startup', action='store_true', dest='no_startup',
            help='When using plain Python, ignore the PYTHONSTARTUP environment variable and ~/.pythonrc.py script.'),
        make_option('-i', '--interface', action='store', type='choice', choices=shells,
                    dest='interface',
            help='Specify an interactive interpreter interface. Available options: "ipython" and "bpython"'),

    )
    help = "Runs a Python interactive interpreter. Tries to use IPython or bpython, if one of them is available."
    requires_model_validation = False

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

    def handle_noargs(self, **options):
        # XXX: (Temporary) workaround for ticket #1796: force early loading of all
        # models from installed apps.
        from django.db.models.loading import get_models
        get_models()

        use_plain = options.get('plain', False)
        no_startup = options.get('no_startup', False)
        interface = options.get('interface', None)

        try:
            if use_plain:
                # Don't bother loading IPython, because the user wants plain Python.
                raise ImportError

            self.run_shell(shell=interface)
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
            if not no_startup:
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

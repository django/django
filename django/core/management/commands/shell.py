import os
import select
import sys
import warnings

from django.core.management import BaseCommand, CommandError
from django.utils.datastructures import OrderedSet
from django.utils.deprecation import RemovedInDjango20Warning


class ShellImportError(Exception):
    """A shell is not installed"""
    pass


class Command(BaseCommand):
    help = (
        "Runs a Python interactive interpreter. Tries to use IPython or "
        "bpython, if one of them is available. Any standard input is executed "
        "as code."
    )

    requires_system_checks = False
    shells = ['ipython', 'bpython', 'python']

    def add_arguments(self, parser):
        parser.add_argument(
            '--plain', action='store_true', dest='plain',
            help='Tells Django to use plain Python, not IPython or bpython. '
                 'Deprecated, use the `-i python` or `--interface python` option instead.',
        )
        parser.add_argument(
            '--no-startup', action='store_true', dest='no_startup',
            help='When using plain Python, ignore the PYTHONSTARTUP environment variable and ~/.pythonrc.py script.',
        )
        parser.add_argument(
            '-i', '--interface', choices=self.shells, dest='interface',
            help='Specify an interactive interpreter interface. Available options: "ipython", "bpython", and "python"',
        )
        parser.add_argument(
            '-c', '--command', dest='command',
            help='Instead of opening an interactive shell, run a command as Django and exit.',
        )

    def _ipython_pre_011(self):
        """Start IPython pre-0.11"""
        try:
            from IPython.Shell import IPShell
        except ImportError:
            raise ShellImportError
        shell = IPShell(argv=[])
        shell.mainloop()

    def _ipython_pre_100(self):
        """Start IPython pre-1.0.0"""
        try:
            from IPython.frontend.terminal.ipapp import TerminalIPythonApp
        except ImportError:
            raise ShellImportError
        app = TerminalIPythonApp.instance()
        app.initialize(argv=[])
        app.start()

    def _ipython(self):
        """Start IPython >= 1.0"""
        try:
            from IPython import start_ipython
        except ImportError:
            raise ShellImportError
        start_ipython(argv=[])

    def ipython(self, options):
        """Start any version of IPython"""
        for ip in (self._ipython, self._ipython_pre_100, self._ipython_pre_011):
            try:
                ip()
            except ShellImportError:
                pass
            else:
                return
        raise ShellImportError("No IPython")

    def bpython(self, options):
        try:
            import bpython
        except ImportError:
            raise ShellImportError("No bpython")
        bpython.embed()

    def python(self, options):
        import code
        # Set up a dictionary to serve as the environment for the shell, so
        # that tab completion works on objects that are imported at runtime.
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
            # Enable tab completion on systems using libedit (e.g. Mac OSX).
            # These lines are copied from Lib/site.py on Python 3.4.
            readline_doc = getattr(readline, '__doc__', '')
            if readline_doc is not None and 'libedit' in readline_doc:
                readline.parse_and_bind("bind ^I rl_complete")
            else:
                readline.parse_and_bind("tab:complete")

        # We want to honor both $PYTHONSTARTUP and .pythonrc.py, so follow system
        # conventions and get $PYTHONSTARTUP first then .pythonrc.py.
        if not options['no_startup']:
            for pythonrc in OrderedSet([os.environ.get("PYTHONSTARTUP"), os.path.expanduser('~/.pythonrc.py')]):
                if not pythonrc:
                    continue
                if not os.path.isfile(pythonrc):
                    continue
                try:
                    with open(pythonrc) as handle:
                        exec(compile(handle.read(), pythonrc, 'exec'), imported_objects)
                except NameError:
                    pass
        code.interact(local=imported_objects)

    def handle(self, **options):
        if options['plain']:
            warnings.warn(
                "The --plain option is deprecated in favor of the -i python or --interface python option.",
                RemovedInDjango20Warning
            )
            options['interface'] = 'python'

        # Execute the command and exit.
        if options['command']:
            exec(options['command'])
            return

        # Execute stdin if it has anything to read and exit.
        # Not supported on Windows due to select.select() limitations.
        if sys.platform != 'win32' and select.select([sys.stdin], [], [], 0)[0]:
            exec(sys.stdin.read())
            return

        if options['interface']:
            shell = options['interface']
            try:
                return getattr(self, shell)(options)
            except ShellImportError:
                raise CommandError("Couldn't import {} interface.".format(shell))
        else:
            for shell in self.shells:
                try:
                    return getattr(self, shell)(options)
                except ShellImportError:
                    pass
            assert False, "Couldn't load any interface."

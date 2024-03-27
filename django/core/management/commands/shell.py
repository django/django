import os
import select
import sys
import traceback

from django.apps import apps
from django.apps.config import MODELS_MODULE_NAME
from django.core.management import BaseCommand, CommandError
from django.utils.datastructures import OrderedSet
from django.utils.module_loading import import_string


class Command(BaseCommand):
    help = (
        "Runs a Python interactive interpreter. Tries to use IPython or "
        "bpython, if one of them is available. Any standard input is executed "
        "as code."
    )

    requires_system_checks = []
    shells = ["ipython", "bpython", "python"]

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-startup",
            action="store_true",
            help=(
                "When using plain Python, ignore the PYTHONSTARTUP environment "
                "variable and ~/.pythonrc.py script."
            ),
        )
        parser.add_argument(
            "-i",
            "--interface",
            choices=self.shells,
            help=(
                "Specify an interactive interpreter interface. Available options: "
                '"ipython", "bpython", and "python"'
            ),
        )
        parser.add_argument(
            "-c",
            "--command",
            help=(
                "Instead of opening an interactive shell, run a command as Django and "
                "exit."
            ),
        )

    def ipython(self, options):
        from IPython import start_ipython

        try:
            imported_objects = self.get_namespace(options, self.style)
            start_ipython(argv=[], user_ns=imported_objects)
        except ImportError:
            traceback.format_exc()

    def bpython(self, options):
        import bpython

        imported_objects = self.get_namespace(options, self.style)
        bpython.embed(imported_objects)

    def python(self, options):
        import code

        # Set up a dictionary to serve as the environment for the shell.
        imported_objects = self.get_namespace(options, self.style)

        # We want to honor both $PYTHONSTARTUP and .pythonrc.py, so follow system
        # conventions and get $PYTHONSTARTUP first then .pythonrc.py.
        if not options["no_startup"]:
            for pythonrc in OrderedSet(
                [os.environ.get("PYTHONSTARTUP"), os.path.expanduser("~/.pythonrc.py")]
            ):
                if not pythonrc:
                    continue
                if not os.path.isfile(pythonrc):
                    continue
                with open(pythonrc) as handle:
                    pythonrc_code = handle.read()
                # Match the behavior of the cpython shell where an error in
                # PYTHONSTARTUP prints an exception and continues.
                try:
                    exec(compile(pythonrc_code, pythonrc, "exec"), imported_objects)
                except Exception:
                    traceback.print_exc()

        # By default, this will set up readline to do tab completion and to read and
        # write history to the .python_history file, but this can be overridden by
        # $PYTHONSTARTUP or ~/.pythonrc.py.
        try:
            hook = sys.__interactivehook__
        except AttributeError:
            # Match the behavior of the cpython shell where a missing
            # sys.__interactivehook__ is ignored.
            pass
        else:
            try:
                hook()
            except Exception:
                # Match the behavior of the cpython shell where an error in
                # sys.__interactivehook__ prints a warning and the exception
                # and continues.
                print("Failed calling sys.__interactivehook__")
                traceback.print_exc()

        # Set up tab completion for objects imported by $PYTHONSTARTUP or
        # ~/.pythonrc.py.
        try:
            import readline
            import rlcompleter

            readline.set_completer(rlcompleter.Completer(imported_objects).complete)
        except ImportError:
            pass

        # Start the interactive interpreter.
        code.interact(local=imported_objects)

    def get_app_name(self, app_module):
        # implementation from django_extension
        rparts = list(reversed(app_module.split(".")))
        try:
            try:
                return rparts[rparts.index(MODELS_MODULE_NAME) + 1]
            except ValueError:
                return rparts[1]
        except IndexError:
            return app_module

    def get_apps_and_models(self):
        # get all apps and models
        for app_conf in apps.get_app_configs():
            if app_conf.models_module:
                yield app_conf.models_module, app_conf.get_models()

    def get_namespace(self, options, style):
        """Override this method with import_items in order to import extra_things"""

        imported_objects = {}

        for app_module, app_models in self.get_apps_and_models():
            if not app_models:
                continue

            for model in app_models:

                if model.__module__:
                    try:
                        imported_objects[model.__name__] = import_string(
                            "%s.%s" % (model.__module__, model.__name__)
                        )
                    except ImportError as e:
                        if options.get("traceback"):
                            traceback.print_exc()
                        else:
                            print(
                                style.ERROR(
                                    "Failed to import %s from %s, reason %s"
                                    % (model.__name__, model.__module__, e)
                                )
                            )

        return imported_objects

    def handle(self, **options):
        # Execute the command and exit.
        if options["command"]:
            exec(options["command"], globals())
            return

        # Execute stdin if it has anything to read and exit.
        # Not supported on Windows due to select.select() limitations.
        if (
            sys.platform != "win32"
            and not sys.stdin.isatty()
            and select.select([sys.stdin], [], [], 0)[0]
        ):
            exec(sys.stdin.read(), globals())
            return

        available_shells = (
            [options["interface"]] if options["interface"] else self.shells
        )

        for shell in available_shells:
            try:
                return getattr(self, shell)(options)
            except ImportError:
                pass
        raise CommandError("Couldn't import {} interface.".format(shell))

import os
import select
import sys
import traceback
from datetime import date, datetime, timedelta

from django.apps import apps
from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.db import models
from django.db.models import functions
from django.utils.datastructures import OrderedSet


class Command(BaseCommand):
    help = (
        "Runs a Python interactive interpreter. Tries to use IPython or "
        "bpython, if one of them is available. Any standard input is executed "
        "as code."
    )

    requires_system_checks = []
    shells = ["ipython", "bpython", "python"]
    default_namespace = {
        "date": date,
        "datetime": datetime,
        "timedelta": timedelta,
        "models": models,
        "functions": functions,
        "settings": settings,
    }

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

        start_ipython(
            argv=[],
            user_ns=self.get_and_report_namespace(options["verbosity"]),
        )

    def bpython(self, options):
        import bpython

        bpython.embed(self.get_and_report_namespace(options["verbosity"]))

    def python(self, options):
        import code

        # Set up a dictionary to serve as the environment for the shell.
        imported_objects = self.get_and_report_namespace(options["verbosity"])

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

    def get_and_report_namespace(self, verbosity):
        namespace = self.get_namespace()

        if verbosity == 1:
            self.stdout.write(
                f"{len(namespace)} objects imported automatically",
                self.style.SUCCESS,
            )
        elif verbosity >= 2:
            imports_by_module = {}
            imports_by_alias = {}
            for obj_name, obj in namespace.items():
                if hasattr(obj, "__module__") and (
                    (hasattr(obj, "__qualname__") and obj.__qualname__.find(".") == -1)
                    or not hasattr(obj, "__qualname__")
                ):
                    module = obj.__module__
                    collected_imports = imports_by_module.get(module, [])
                    imports_by_module[module] = collected_imports + [obj_name]
                if not hasattr(obj, "__module__"):
                    tokens = obj.__name__.split(".")
                    if obj_name in tokens:
                        tokens.remove(obj_name)
                        module = ".".join(tokens)
                        collected_imports = imports_by_module.get(module, [])
                        imports_by_module[module] = collected_imports + [obj_name]
                    else:
                        module = ".".join(tokens)
                        imports_by_alias[module] = obj_name

            for module, imported_objects in imports_by_module.items():
                self.stdout.write(
                    f"from {module} import {', '.join(imported_objects)}",
                    self.style.SUCCESS,
                )
            for module, alias in imports_by_alias.items():
                self.stdout.write(f"import {module} as {alias}", self.style.SUCCESS)

        return namespace

    def get_namespace(self):
        apps_models = apps.get_models()
        apps_models_modules = [
            (app.models_module, app.label)
            for app in apps.get_app_configs()
            if app.models_module is not None
        ]
        namespace = {}
        for label in self.default_namespace:
            namespace[label] = self.default_namespace[label]
        for model in reversed(apps_models):
            if model.__module__:
                namespace[model.__name__] = model
        for app_models_module, app_label in apps_models_modules:
            namespace[f"{app_label}_models"] = app_models_module
        return namespace

    def handle(self, **options):
        # Execute the command and exit.
        if options["command"]:
            exec(options["command"], {**globals(), **self.get_namespace()})
            return

        # Execute stdin if it has anything to read and exit.
        # Not supported on Windows due to select.select() limitations.
        if (
            sys.platform != "win32"
            and not sys.stdin.isatty()
            and select.select([sys.stdin], [], [], 0)[0]
        ):
            exec(sys.stdin.read(), {**globals(), **self.get_namespace()})
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

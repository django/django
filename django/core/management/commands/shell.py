import os
import select
import sys
import traceback
from collections import defaultdict
from importlib import import_module

from django.apps import apps
from django.core.exceptions import AppRegistryNotReady
from django.core.management import BaseCommand, CommandError
from django.utils.datastructures import OrderedSet
from django.utils.module_loading import import_string as import_dotted_path


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
            "--no-imports",
            action="store_true",
            help="Disable automatic imports of models.",
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

        start_ipython(argv=[], user_ns=self.get_namespace(**options))

    def bpython(self, options):
        import bpython

        bpython.embed(self.get_namespace(**options))

    def python(self, options):
        import code

        # Set up a dictionary to serve as the environment for the shell.
        imported_objects = self.get_namespace(**options)

        # We want to honor both $PYTHONSTARTUP and .pythonrc.py, so follow
        # system conventions and get $PYTHONSTARTUP first then .pythonrc.py.
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

        # By default, this will set up readline to do tab completion and to
        # read and write history to the .python_history file, but this can be
        # overridden by $PYTHONSTARTUP or ~/.pythonrc.py.
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

    def get_auto_imports(self):
        """Return a sequence of import paths for objects to be auto-imported.

        By default, import paths for models in INSTALLED_APPS and some common
        utilities are included, with models from earlier apps taking precedence
        in case of a name collision.

        For example, for an unchanged INSTALLED_APPS, this method returns:

        [
            "django.conf.settings",
            "django.db.connection",
            "django.db.models",
            "django.db.models.functions",
            "django.db.reset_queries",
            "django.utils.timezone",
            "django.contrib.sessions.models.Session",
            "django.contrib.contenttypes.models.ContentType",
            "django.contrib.auth.models.User",
            "django.contrib.auth.models.Group",
            "django.contrib.auth.models.Permission",
            "django.contrib.admin.models.LogEntry",
        ]

        """
        default_imports = [
            "django.conf.settings",
            "django.db.connection",
            "django.db.models",
            "django.db.models.functions",
            "django.db.reset_queries",
            "django.utils.timezone",
        ]
        app_models_imports = default_imports + [
            f"{model.__module__}.{model.__name__}"
            for model in reversed(apps.get_models())
            if model.__module__
        ]
        return app_models_imports

    def get_namespace(self, **options):
        if options and options.get("no_imports"):
            return {}

        verbosity = options["verbosity"] if options else 0

        try:
            apps.check_models_ready()
        except AppRegistryNotReady:
            if verbosity > 0:
                settings_env_var = os.getenv("DJANGO_SETTINGS_MODULE")
                self.stdout.write(
                    "Automatic imports are disabled since settings are not configured."
                    f"\nDJANGO_SETTINGS_MODULE value is {settings_env_var!r}.\n"
                    "HINT: Ensure that the settings module is configured and set.",
                    self.style.ERROR,
                    ending="\n\n",
                )
            return {}

        path_imports = self.get_auto_imports()
        if path_imports is None:
            return {}

        auto_imports = defaultdict(list)
        import_errors = []
        for path in path_imports:
            try:
                obj = import_dotted_path(path) if "." in path else import_module(path)
            except ImportError:
                import_errors.append(path)
                continue

            if "." in path:
                module, name = path.rsplit(".", 1)
            else:
                module = None
                name = path
            if (name, obj) not in auto_imports[module]:
                auto_imports[module].append((name, obj))

        namespace = {
            name: obj for items in auto_imports.values() for name, obj in items
        }

        if verbosity < 1:
            return namespace

        errors = len(import_errors)
        if errors:
            msg = "\n".join(f"  {e}" for e in import_errors)
            objects = "objects" if errors != 1 else "object"
            self.stdout.write(
                f"{errors} {objects} could not be automatically imported:\n\n{msg}",
                self.style.ERROR,
                ending="\n\n",
            )

        amount = len(namespace)
        objects_str = "objects" if amount != 1 else "object"
        msg = f"{amount} {objects_str} imported automatically"

        if verbosity < 2:
            if amount:
                msg += " (use -v 2 for details)"
            self.stdout.write(f"{msg}.", self.style.SUCCESS, ending="\n\n")
            return namespace

        top_level = auto_imports.pop(None, [])
        import_string = "\n".join(
            [f"  import {obj}" for obj, _ in top_level]
            + [
                f"  from {module} import {objects}"
                for module, imported_objects in auto_imports.items()
                if (objects := ", ".join(i[0] for i in imported_objects))
            ]
        )

        try:
            import isort
        except ImportError:
            pass
        else:
            import_string = isort.code(import_string)

        if import_string:
            msg = f"{msg}:\n\n{import_string}"
        else:
            msg = f"{msg}."

        self.stdout.write(msg, self.style.SUCCESS, ending="\n\n")

        return namespace

    def handle(self, **options):
        # Execute the command and exit.
        if options["command"]:
            exec(options["command"], {**globals(), **self.get_namespace(**options)})
            return

        # Execute stdin if it has anything to read and exit.
        # Not supported on Windows due to select.select() limitations.
        if (
            sys.platform != "win32"
            and not sys.stdin.isatty()
            and select.select([sys.stdin], [], [], 0)[0]
        ):
            exec(sys.stdin.read(), {**globals(), **self.get_namespace(**options)})
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

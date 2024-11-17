import os
import select
import sys
import traceback
import importlib

from django.core.management import BaseCommand, CommandError
from django.utils.datastructures import OrderedSet
from django.apps import apps
import django


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

        start_ipython(argv=[])

    def bpython(self, options):
        import bpython

        bpython.embed()

    def python(self, options):
        import code

        # Set up a dictionary to serve as the environment for the shell.
        imported_objects = {}

        # Automatically set up Django environment
        django.setup()

        # Auto-import all models from installed apps
        self.auto_import_models(imported_objects)

        # Allow users to customize the shell by adding extra imports
        self.add_custom_imports(imported_objects)

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
            pass
        else:
            try:
                hook()
            except Exception:
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

        # Start the interactive interpreter with auto-imported models and custom imports.
        code.interact(local=imported_objects)

    def auto_import_models(self, imported_objects):
        """Auto-import all models from installed Django apps."""
        for app_config in apps.get_app_configs():
            try:
                if hasattr(app_config.module, 'models'):
                    models_module = app_config.module.models
                    self.import_models_from_module(models_module, app_config.label, imported_objects)
            except ModuleNotFoundError:
                pass

    def import_models_from_module(self, models_module, app_name, imported_objects):
        """Imports models from the module and handles name collisions."""
        try:
            # Dynamically import models module
            models = importlib.import_module(f'{models_module.__name__}')
            for model_name, model in vars(models).items():
                if hasattr(model, '_meta'):
                    # Create a unique key for the model to avoid name collision
                    unique_name = f"{app_name}_{model_name}"
                    imported_objects[unique_name] = model
                    imported_objects.update(
                        {model.__name__: model for model in vars(models_module).values() if hasattr(model, '_meta')}
                    )
                    print(f"Auto-imported model {model_name} from {app_name}")
        except ImportError as e:
            print(f"Failed to import models from {app_name}: {e}")

    def add_custom_imports(self, imported_objects):
        """
        Allow users to customize the shell by adding extra methods or classes.
        Users can subclass this command and override this method to add their own imports.
        """
        # Example custom import (Users can override this method to add their own)
        try:
            # Importing any additional utilities or classes
            from datetime import datetime
            imported_objects['datetime'] = datetime
            print("Auto-imported custom utilities (e.g., datetime)")
        except ImportError:
            pass

    def handle(self, **options):
        # Execute the command and exit.
        if options["command"]:
            exec(options["command"], globals())
            return

        # Execute stdin if it has anything to read and exit.
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
        raise CommandError(f"Couldn't import {options['interface']} interface.")

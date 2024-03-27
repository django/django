import os
import select
import sys
import traceback

from django.apps import apps
from django.core.management import BaseCommand, CommandError
from django.utils.datastructures import OrderedSet
from django.utils.module_loading import import_string

CHANGED_IMPORTS = [
    {"cache": "django.core.cache.cache"},
    {"settings": "django.conf.settings"},
    {"get_user_model": "django.contrib.auth.get_user_model"},
    {"transaction": "django.db.transaction"},
    {"Avg": "django.db.models.Avg"},
    {"Case": "django.db.models.Case"},
    {"Count": "django.db.models.Count"},
    {"F": "django.db.models.F"},
    {"Max": "django.db.models.Max"},
    {"Min": "django.db.models.Min"},
    {"Prefetch": "django.db.models.Prefetch"},
    {"Q": "django.db.models.Q"},
    {"Sum": "django.db.models.Sum"},
    {"When": "django.db.models.When"},
    {"timezone": "django.utils.timezone"},
    {"reverse": "django.urls.reverse"},
    {"Exists": "django.db.models.Exists"},
]


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

        def run_ipython():
            my_models = {}
            imported_objects = self.get_objects(self.style)
            for app_mod, app_models in self.get_apps_and_models():
                for mod in app_models:
                    if mod.__module__:
                        my_models.setdefault(mod.__module__, [])
                        my_models[mod.__module__].append(mod.__name__)
            imported_objects.update(self.get_app_models(my_models, self.style))
            start_ipython(argv=[], user_ns=imported_objects)

        return run_ipython()

    def bpython(self, options):
        import bpython

        bpython.embed()

    def python(self, options):
        import code

        my_models = {}
        imported_objects = self.get_objects(self.style)
        for app_mod, app_models in self.get_apps_and_models():
            for mod in app_models:
                if mod.__module__:
                    my_models.setdefault(mod.__module__, [])
                    my_models[mod.__module__].append(mod.__name__)
        imported_objects.update(self.get_app_models(my_models, self.style))

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

    def get_objects(self, style):
        import_objects = {}
        default_modules_counter = 0
        module_names = ""
        for x in CHANGED_IMPORTS:
            for key, val in x.items():
                import_objects[key] = import_string(val)
                default_modules_counter += 1
                module_names += str(key) + " "
        module_names = module_names.strip()
        print(
            style.SUCCESS(
                f"imported {default_modules_counter} default objects ({module_names})"
            )
        )
        return import_objects

    def get_apps_and_models(self):
        for app in apps.get_app_configs():
            if app.models_module:
                yield app.models_module, app.get_models()

    def get_app_models(self, load_models, style):
        import_objects = {}
        model_counter = 0
        model_names = ""
        for key, val in load_models.items():
            if len(val) >= 1:
                for x in val:
                    import_objects[x] = import_string(str(key) + "." + str(x))
                    model_counter += 1
                    model_names += str(x) + " "
        model_names = model_names.strip()
        print(style.SUCCESS(f"imported {model_counter} app models ({model_names})"))
        return import_objects

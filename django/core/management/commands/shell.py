import os
from django.core.management.base import NoArgsCommand
from optparse import make_option


class Command(NoArgsCommand):
    shells = ['ipython', 'bpython']

    option_list = NoArgsCommand.option_list + (
        make_option('--plain', action='store_true', dest='plain',
            help='Tells Django to use plain Python, not IPython or bpython.'),
        make_option('-i', '--interface', action='store', type='choice', choices=shells,
                    dest='interface',
            help='Specify an interactive interpreter interface. Available options: "ipython" and "bpython"'),

    )
    help = "Runs a Python interactive interpreter. Tries to use IPython or bpython, if one of them is available."
    requires_model_validation = False
    
    def get_initial_shell_locals(self):
        """
         returns a dict to use for local package imports
         
         Sample settings:
         SHELL_IMPORTS_ALL_MODELS = True
         SHELL_IMPORTS = [
            'django.db.models.Q',
            'haystack.query.SearchQuerySet'
         ]
        """
        
        from django.conf import settings
        shell_locals = {}
        
        if getattr(settings, 'SHELL_IMPORTS_ALL_MODELS', False):
            from django.db.models.loading import get_models
            
            all_models   = get_models()
            shell_locals.update(dict([[m.__name__, m] for m in all_models]))
            
        for item in getattr(settings, 'SHELL_IMPORTS', []):
            if '.' in item:
                item_parts = item.split('.')
                module_name = '.'.join(item_parts[:-1])
                import_name = item_parts[-1]
                resulting_import = __import__(module_name, fromlist=[import_name])
                shell_locals[import_name] = resulting_import
            else:
                shell_locals[item] = __import__(item)
        
        return shell_locals
    
    def ipython(self):
        try:
            from IPython import embed
            embed(local_ns=self.get_initial_shell_locals())
        except ImportError:
            # IPython < 0.11
            # Explicitly pass an empty list as arguments, because otherwise
            # IPython would use sys.argv from this script.
            try:
                from IPython.Shell import IPShell
                shell = IPShell(argv=[])
                shell.mainloop()
            except ImportError:
                # IPython not found at all, raise ImportError
                raise

    def bpython(self):
        import bpython
        bpython.embed(locals_=self.get_initial_shell_locals())

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
            imported_objects = self.get_initial_shell_locals()
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
            # conventions and get $PYTHONSTARTUP first then import user.
            if not use_plain:
                pythonrc = os.environ.get("PYTHONSTARTUP")
                if pythonrc and os.path.isfile(pythonrc):
                    try:
                        execfile(pythonrc)
                    except NameError:
                        pass
                # This will import .pythonrc.py as a side-effect
                import user
            code.interact(local=imported_objects)

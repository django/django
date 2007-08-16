from django.core.management.base import NoArgsCommand

def module_to_dict(module, omittable=lambda k: k.startswith('_')):
    "Converts a module namespace to a Python dictionary. Used by get_settings_diff."
    return dict([(k, repr(v)) for k, v in module.__dict__.items() if not omittable(k)])

class Command(NoArgsCommand):
    help = """Displays differences between the current settings.py and Django's
    default settings. Settings that don't appear in the defaults are
    followed by "###"."""

    requires_model_validation = False

    def handle_noargs(self, **options):
        # Inspired by Postfix's "postconf -n".
        from django.conf import settings, global_settings

        # Because settings are imported lazily, we need to explicitly load them.
        settings._import_settings()

        user_settings = module_to_dict(settings._target)
        default_settings = module_to_dict(global_settings)

        output = []
        keys = user_settings.keys()
        keys.sort()
        for key in keys:
            if key not in default_settings:
                output.append("%s = %s  ###" % (key, user_settings[key]))
            elif user_settings[key] != default_settings[key]:
                output.append("%s = %s" % (key, user_settings[key]))
        print '\n'.join(output)

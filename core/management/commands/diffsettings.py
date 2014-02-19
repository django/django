from optparse import make_option

from django.core.management.base import NoArgsCommand


def module_to_dict(module, omittable=lambda k: k.startswith('_')):
    """Converts a module namespace to a Python dictionary."""
    return dict((k, repr(v)) for k, v in module.__dict__.items() if not omittable(k))


class Command(NoArgsCommand):
    help = """Displays differences between the current settings.py and Django's
    default settings. Settings that don't appear in the defaults are
    followed by "###"."""

    option_list = NoArgsCommand.option_list + (
        make_option('--all', action='store_true', dest='all', default=False,
                    help='Display all settings, regardless of their value. '
                         'Default values are prefixed by "###".'),
    )

    requires_system_checks = False

    def handle_noargs(self, **options):
        # Inspired by Postfix's "postconf -n".
        from django.conf import settings, global_settings

        # Because settings are imported lazily, we need to explicitly load them.
        settings._setup()

        user_settings = module_to_dict(settings._wrapped)
        default_settings = module_to_dict(global_settings)

        output = []
        for key in sorted(user_settings):
            if key not in default_settings:
                output.append("%s = %s  ###" % (key, user_settings[key]))
            elif user_settings[key] != default_settings[key]:
                output.append("%s = %s" % (key, user_settings[key]))
            elif options['all']:
                output.append("### %s = %s" % (key, user_settings[key]))
        return '\n'.join(output)

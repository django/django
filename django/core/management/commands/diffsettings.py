from django.core.management.base import BaseCommand


def module_to_dict(module, omittable=lambda k: k.startswith('_')):
    """Convert a module namespace to a Python dictionary."""
    return {k: repr(v) for k, v in module.__dict__.items() if not omittable(k)}


class Command(BaseCommand):
    help = """Displays differences between the current settings.py and Django's
    default settings."""

    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument(
            '--all', action='store_true', dest='all',
            help=(
                'Display all settings, regardless of their value. In "hash" '
                'mode, default values are prefixed by "###".'
            ),
        )
        parser.add_argument(
            '--default', dest='default', metavar='MODULE', default=None,
            help=(
                "The settings module to compare the current settings against. Leave empty to "
                "compare against Django's default settings."
            ),
        )
        parser.add_argument(
            '--output', default='hash', choices=('hash', 'unified'), dest='output',
            help=(
                "Selects the output format. 'hash' mode displays each changed "
                "setting, with the settings that don't appear in the defaults "
                "followed by ###. 'unified' mode prefixes the default setting "
                "with a minus sign, followed by the changed setting prefixed "
                "with a plus sign."
            ),
        )

    def handle(self, **options):
        from django.conf import settings, Settings, global_settings

        # Because settings are imported lazily, we need to explicitly load them.
        settings._setup()

        user_settings = module_to_dict(settings._wrapped)
        default = options['default']
        default_settings = module_to_dict(Settings(default) if default else global_settings)
        output_func = {
            'hash': self.output_hash,
            'unified': self.output_unified,
        }[options['output']]
        return '\n'.join(output_func(user_settings, default_settings, **options))

    def output_hash(self, user_settings, default_settings, **options):
        # Inspired by Postfix's "postconf -n".
        output = []
        for key in sorted(user_settings):
            if key not in default_settings:
                output.append("%s = %s  ###" % (key, user_settings[key]))
            elif user_settings[key] != default_settings[key]:
                output.append("%s = %s" % (key, user_settings[key]))
            elif options['all']:
                output.append("### %s = %s" % (key, user_settings[key]))
        return output

    def output_unified(self, user_settings, default_settings, **options):
        output = []
        for key in sorted(user_settings):
            if key not in default_settings:
                output.append(self.style.SUCCESS("+ %s = %s" % (key, user_settings[key])))
            elif user_settings[key] != default_settings[key]:
                output.append(self.style.ERROR("- %s = %s" % (key, default_settings[key])))
                output.append(self.style.SUCCESS("+ %s = %s" % (key, user_settings[key])))
            elif options['all']:
                output.append("  %s = %s" % (key, user_settings[key]))
        return output

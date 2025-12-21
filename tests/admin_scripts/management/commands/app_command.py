from django.core.management.base import AppCommand


class Command(AppCommand):
    help = "Test Application-based commands"
    requires_system_checks = []

    def handle_app_config(self, app_config, **options):
        print(
            f"EXECUTE:AppCommand name={app_config.name}, options={sorted(options.items())}"
        )

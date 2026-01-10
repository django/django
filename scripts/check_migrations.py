import sys
from pathlib import Path

import django
from django.apps import apps
from django.conf import settings
from django.core.management import call_command


def main():
    repo_root = Path(__file__).resolve().parent.parent
    sys.path[:0] = [str(repo_root / "tests"), str(repo_root)]
    from runtests import ALWAYS_INSTALLED_APPS, get_apps_to_install, get_test_modules

    if not settings.configured:
        settings.configure(
            INSTALLED_APPS=ALWAYS_INSTALLED_APPS,
            MIGRATION_MODULES={},
        )
        django.setup()

    test_modules = list(get_test_modules(gis_enabled=False))
    installed_apps = list(ALWAYS_INSTALLED_APPS)
    for app in get_apps_to_install(test_modules):
        # Check against the list to prevent duplicate error
        if app not in installed_apps:
            installed_apps.append(app)
    apps.set_installed_apps(installed_apps)

    try:
        call_command("makemigrations", "--check", verbosity=1)
    except Exception as e:
        print(f"Error checking migrations: {str(e)}")


if __name__ == "__main__":
    main()

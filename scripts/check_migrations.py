import sys
from pathlib import Path


def main():
    repo_root = Path(__file__).resolve().parent.parent
    sys.path[:0] = [str(repo_root / "tests"), str(repo_root)]

    from runtests import ALWAYS_INSTALLED_APPS, get_apps_to_install, get_test_modules

    import django
    from django.apps import apps
    from django.core.management import call_command

    django.setup()

    test_modules = list(get_test_modules(gis_enabled=False))
    installed_apps = list(ALWAYS_INSTALLED_APPS)
    for app in get_apps_to_install(test_modules):
        # Check against the list to prevent duplicate errors.
        if app not in installed_apps:
            installed_apps.append(app)
    apps.set_installed_apps(installed_apps)

    # Note: We don't use check=True here because --check calls sys.exit(1)
    # instead of raising CommandError when migrations are missing.
    call_command("makemigrations", "--check", verbosity=3)


if __name__ == "__main__":
    main()

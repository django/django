"""CI helper: run `makemigrations --check` for test apps.

This script sets DJANGO_SETTINGS_MODULE to the default test settings
(`test_sqlite`) and runs `django.core.management`'s `call_command` for
`makemigrations --check`. It exits with a non-zero status if migrations
are needed.

Designed to be executed in CI from the repository root using the
checked-out Django package.
"""

import os
import sys

from django.core.management import call_command


def main():
    # Use the test settings used by the test runner by default.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_sqlite")

    # Ensure the project's parent directory is on sys.path so `django`
    # imports resolve to the checked-out tree when running in CI.
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if here not in sys.path:
        sys.path.insert(0, here)

    try:
        # Ensure the test settings module is importable (tests live in the
        # repository root `tests/` directory and can be imported as
        # `test_sqlite` when the repo root is on sys.path).
        try:
            __import__(os.environ["DJANGO_SETTINGS_MODULE"])
        except Exception:
            tests_dir = os.path.join(here, "tests")
            if tests_dir not in sys.path:
                sys.path.insert(0, tests_dir)
        import django

        django.setup()

        # --check exits the process with SystemExit on failure; propagate it
        # so CI will fail. We silence output on success.
        call_command("makemigrations", "--check", verbosity=0)
    except SystemExit:
        # Rerun with verbosity=1 to show details in CI logs.
        try:
            call_command("makemigrations", "--check", verbosity=1)
        except SystemExit:
            pass
        raise


if __name__ == "__main__":
    main()

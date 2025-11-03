import getpass
import sys

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections

UserModel = get_user_model()


class Command(BaseCommand):
    help = "Change a user's password for django.contrib.auth."
    requires_migrations_checks = True
    requires_system_checks = []

    def _get_pass(self, prompt="Password: "):
        p = getpass.getpass(prompt=prompt)
        if not p:
            raise CommandError("aborted")
        return p

    def _get_stdin(self):
        try:
            stdin_content = sys.stdin.readline()
            return stdin_content, stdin_content
        except Exception:
            raise CommandError("aborted")

    def add_arguments(self, parser):
        parser.add_argument(
            "username",
            nargs="?",
            help=(
                "Username to change password for; by default, it's the current "
                "username."
            ),
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            choices=tuple(connections),
            help='Specifies the database to use. Default is "default".',
        )
        parser.add_argument(
            "--stdin",
            action="store_true",
            help="Read new password from stdin rather than prompting, default is False",
        )

    def handle(self, *args, **options):
        def _input_getter_getpass():
            p1 = self._get_pass()
            p2 = self._get_pass("Password (again): ")
            return p1, p2

        def _input_getter_stdin():
            return self._get_stdin()

        if options["username"]:
            username = options["username"]
        else:
            username = getpass.getuser()

        if options["stdin"]:
            input_getter = _input_getter_stdin
        else:
            input_getter = _input_getter_getpass
        try:
            u = UserModel._default_manager.using(options["database"]).get(
                **{UserModel.USERNAME_FIELD: username}
            )
        except UserModel.DoesNotExist:
            raise CommandError("user '%s' does not exist" % username)

        self.stdout.write("Changing password for user '%s'" % u)

        MAX_TRIES = 3
        count = 0
        p1, p2 = 1, 2  # To make them initially mismatch.
        password_validated = False
        while (p1 != p2 or not password_validated) and count < MAX_TRIES:
            p1, p2 = input_getter()
            if p1 != p2:
                self.stdout.write("Passwords do not match. Please try again.")
                count += 1
                # Don't validate passwords that don't match.
                continue
            try:
                validate_password(p2, u)
            except ValidationError as err:
                self.stderr.write("\n".join(err.messages))
                count += 1
            else:
                password_validated = True

        if count == MAX_TRIES:
            raise CommandError(
                "Aborting password change for user '%s' after %s attempts" % (u, count)
            )

        u.set_password(p1)
        u.save()

        return "Password changed successfully for user '%s'" % u

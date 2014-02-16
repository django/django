from __future__ import unicode_literals

import getpass
from optparse import make_option

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Specifies the database to use. Default is "default".'),
        make_option('--read-stdin', action='store', dest='read_stdin',
            default=False, help='Read data from stdin')
    )
    help = "Change a user's password for django.contrib.auth."

    requires_system_checks = False

    def _get_pass(self, read_stdin, prompt="Password: "):
        if not read_stdin:
            p = getpass.getpass(prompt=prompt)
            if not p:
                raise CommandError("aborted")
            return p
        else:
            return self.stdin.read()

    def handle(self, *args, **options):
        if len(args) > 1:
            raise CommandError("need exactly one or zero arguments for username")

        read_stdin = options.get('read_stdin')
        if args:
            username, = args
        else:
            if not read_stdin:
                username = getpass.getuser()
            else:
                username = self.stdin.read()

        UserModel = get_user_model()

        try:
            u = UserModel._default_manager.using(options.get('database')).get(**{
                UserModel.USERNAME_FIELD: username
            })
        except UserModel.DoesNotExist:
            raise CommandError("user '%s' does not exist" % username)

        self.stdout.write("Changing password for user '%s'\n" % u)

        MAX_TRIES = 3
        count = 0
        p1, p2 = 1, 2  # To make them initially mismatch.
        while p1 != p2 and count < MAX_TRIES:
            p1 = self._get_pass(read_stdin)
            p2 = self._get_pass(read_stdin, "Password (again): ")
            if p1 != p2:
                self.stdout.write("Passwords do not match. Please try again.\n")
                count = count + 1

        if count == MAX_TRIES:
            raise CommandError("Aborting password change for user '%s' after %s attempts" % (u, count))

        u.set_password(p1)
        u.save()

        return "Password changed successfully for user '%s'" % u

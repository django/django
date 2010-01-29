from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
import getpass

class Command(BaseCommand):
    help = "Change a user's password for django.contrib.auth."

    requires_model_validation = False

    def _get_pass(self, prompt="Password: "):
        p = getpass.getpass(prompt=prompt)
        if not p:
            raise CommandError("aborted")
        return p

    def handle(self, *args, **options):
        if len(args) > 1:
            raise CommandError("need exactly one or zero arguments for username")

        if args:
            username, = args
        else:
            username = getpass.getuser()

        try:
            u = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError("user '%s' does not exist" % username)

        print "Changing password for user '%s'" % u.username

        MAX_TRIES = 3
        count = 0
        p1, p2 = 1, 2  # To make them initially mismatch.
        while p1 != p2 and count < MAX_TRIES:
            p1 = self._get_pass()
            p2 = self._get_pass("Password (again): ")
            if p1 != p2:
                print "Passwords do not match. Please try again."
                count = count + 1

        if count == MAX_TRIES:
            raise CommandError("Aborting password change for user '%s' after %s attempts" % (username, count))

        u.set_password(p1)
        u.save()

        return "Password changed successfully for user '%s'" % u.username

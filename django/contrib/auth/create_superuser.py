"""
Helper function for creating superusers in the authentication system.

If run from the command line, this module lets you create a superuser
interactively.
"""

from django.core import validators
from django.contrib.auth.models import User
import getpass
import os
import sys

def createsuperuser(username=None, email=None, password=None):
    """
    Helper function for creating a superuser from the command line. All
    arguments are optional and will be prompted-for if invalid or not given.
    """
    try:
        import pwd
    except ImportError:
        default_username = ''
    else:
        # Determine the current system user's username, to use as a default.
        default_username = pwd.getpwuid(os.getuid())[0].replace(' ', '').lower()

    # Determine whether the default username is taken, so we don't display
    # it as an option.
    if default_username:
        try:
            User.objects.get(username=default_username)
        except User.DoesNotExist:
            pass
        else:
            default_username = ''

    try:
        while 1:
            if not username:
                input_msg = 'Username'
                if default_username:
                    input_msg += ' (Leave blank to use %r)' % default_username
                username = raw_input(input_msg + ': ')
            if default_username and username == '':
                username = default_username
            if not username.isalnum():
                sys.stderr.write("Error: That username is invalid. Use only letters, digits and underscores.\n")
                username = None
            try:
                User.objects.get(username=username)
            except User.DoesNotExist:
                break
            else:
                sys.stderr.write("Error: That username is already taken.\n")
                username = None
        while 1:
            if not email:
                email = raw_input('E-mail address: ')
            try:
                validators.isValidEmail(email, None)
            except validators.ValidationError:
                sys.stderr.write("Error: That e-mail address is invalid.\n")
                email = None
            else:
                break
        while 1:
            if not password:
                password = getpass.getpass()
                password2 = getpass.getpass('Password (again): ')
                if password != password2:
                    sys.stderr.write("Error: Your passwords didn't match.\n")
                    password = None
                    continue
            if password.strip() == '':
                sys.stderr.write("Error: Blank passwords aren't allowed.\n")
                password = None
                continue
            break
    except KeyboardInterrupt:
        sys.stderr.write("\nOperation cancelled.\n")
        sys.exit(1)
    u = User.objects.create_user(username, email, password)
    u.is_staff = True
    u.is_active = True
    u.is_superuser = True
    u.save()
    print "Superuser created successfully."

if __name__ == "__main__":
    createsuperuser()

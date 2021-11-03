"""
Management utility to create superusers.
"""
import getpass
import os
import sys

from django.contrib.auth import get_user_model
from django.contrib.auth.management import get_default_username
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS
from django.utils.text import capfirst


class NotRunningInTTYException(Exception):
    pass


PASSWORD_FIELD = 'password'


class Command(BaseCommand):
    help = 'Used to create a superuser.'
    requires_migrations_checks = True
    stealth_options = ('stdin',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.UserModel = get_user_model()
        self.username_field = self.UserModel._meta.get_field(self.UserModel.USERNAME_FIELD)

    def add_arguments(self, parser):
        parser.add_argument(
            '--%s' % self.UserModel.USERNAME_FIELD,
            help='Specifies the login for the superuser.',
        )
        parser.add_argument(
            '--noinput', '--no-input', action='store_false', dest='interactive',
            help=(
                'Tells Django to NOT prompt the user for input of any kind. '
                'You must use --%s with --noinput, along with an option for '
                'any other required field. Superusers created with --noinput will '
                'not be able to log in until they\'re given a valid password.' %
                self.UserModel.USERNAME_FIELD
            ),
        )
        parser.add_argument(
            '--database',
            default=DEFAULT_DB_ALIAS,
            help='Specifies the database to use. Default is "default".',
        )
        for field_name in self.UserModel.REQUIRED_FIELDS:
            field = self.UserModel._meta.get_field(field_name)
            if field.many_to_many:
                if field.remote_field.through and not field.remote_field.through._meta.auto_created:
                    raise CommandError(
                        "Required field '%s' specifies a many-to-many "
                        "relation through model, which is not supported."
                        % field_name
                    )
                else:
                    parser.add_argument(
                        '--%s' % field_name, action='append',
                        help=(
                            'Specifies the %s for the superuser. Can be used '
                            'multiple times.' % field_name,
                        ),
                    )
            else:
                parser.add_argument(
                    '--%s' % field_name,
                    help='Specifies the %s for the superuser.' % field_name,
                )

    def execute(self, *args, **options):
        self.stdin = options.get('stdin', sys.stdin)  # Used for testing
        return super().execute(*args, **options)

    def handle(self, *args, **options):
        username = options[self.UserModel.USERNAME_FIELD]
        database = options['database']
        user_data = {}
        verbose_field_name = self.username_field.verbose_name
        try:
            self.UserModel._meta.get_field(PASSWORD_FIELD)
        except exceptions.FieldDoesNotExist:
            pass
        else:
            # If not provided, create the user with an unusable password.
            user_data[PASSWORD_FIELD] = None
        try:
            if options['interactive']:
                # Same as user_data but without many to many fields and with
                # foreign keys as fake model instances instead of raw IDs.
                fake_user_data = {}
                if hasattr(self.stdin, 'isatty') and not self.stdin.isatty():
                    raise NotRunningInTTYException
                default_username = get_default_username(database=database)
                if username:
                    error_msg = self._validate_username(username, verbose_field_name, database)
                    if error_msg:
                        self.stderr.write(error_msg)
                        username = None
                elif username == '':
                    raise CommandError('%s cannot be blank.' % capfirst(verbose_field_name))
                # Prompt for username.
                while username is None:
                    message = self._get_input_message(self.username_field, default_username)
                    username = self.get_input_data(self.username_field, message, default_username)
                    if username:
                        error_msg = self._validate_username(username, verbose_field_name, database)
                        if error_msg:
                            self.stderr.write(error_msg)
                            username = None
                            continue
                user_data[self.UserModel.USERNAME_FIELD] = username
                fake_user_data[self.UserModel.USERNAME_FIELD] = (
                    self.username_field.remote_field.model(username)
                    if self.username_field.remote_field else username
                )
                # Prompt for required fields.
                for field_name in self.UserModel.REQUIRED_FIELDS:
                    field = self.UserModel._meta.get_field(field_name)
                    user_data[field_name] = options[field_name]
                    if user_data[field_name] is not None:
                        user_data[field_name] = field.clean(user_data[field_name], None)
                    while user_data[field_name] is None:
                        message = self._get_input_message(field)
                        input_value = self.get_input_data(field, message)
                        user_data[field_name] = input_value
                        if field.many_to_many and input_value:
                            if not input_value.strip():
                                user_data[field_name] = None
                                self.stderr.write('Error: This field cannot be blank.')
                                continue
                            user_data[field_name] = [pk.strip() for pk in input_value.split(',')]

                    if not field.many_to_many:
                        fake_user_data[field_name] = user_data[field_name]
                    # Wrap any foreign keys in fake model instances.
                    if field.many_to_one:
                        fake_user_data[field_name] = field.remote_field.model(user_data[field_name])

                # Prompt for a password if the model has one.
                while PASSWORD_FIELD in user_data and user_data[PASSWORD_FIELD] is None:
                    password = getpass.getpass()
                    password2 = getpass.getpass('Password (again): ')
                    if password != password2:
                        self.stderr.write("Error: Your passwords didn't match.")
                        # Don't validate passwords that don't match.
                        continue
                    if password.strip() == '':
                        self.stderr.write("Error: Blank passwords aren't allowed.")
                        # Don't validate blank passwords.
                        continue
                    try:
                        validate_password(password2, self.UserModel(**fake_user_data))
                    except exceptions.ValidationError as err:
                        self.stderr.write('\n'.join(err.messages))
                        response = input('Bypass password validation and create user anyway? [y/N]: ')
                        if response.lower() != 'y':
                            continue
                    user_data[PASSWORD_FIELD] = password
            else:
                # Non-interactive mode.
                # Use password from environment variable, if provided.
                if PASSWORD_FIELD in user_data and 'DJANGO_SUPERUSER_PASSWORD' in os.environ:
                    user_data[PASSWORD_FIELD] = os.environ['DJANGO_SUPERUSER_PASSWORD']
                # Use username from environment variable, if not provided in
                # options.
                if username is None:
                    username = os.environ.get('DJANGO_SUPERUSER_' + self.UserModel.USERNAME_FIELD.upper())
                if username is None:
                    raise CommandError('You must use --%s with --noinput.' % self.UserModel.USERNAME_FIELD)
                else:
                    error_msg = self._validate_username(username, verbose_field_name, database)
                    if error_msg:
                        raise CommandError(error_msg)

                user_data[self.UserModel.USERNAME_FIELD] = username
                for field_name in self.UserModel.REQUIRED_FIELDS:
                    env_var = 'DJANGO_SUPERUSER_' + field_name.upper()
                    value = options[field_name] or os.environ.get(env_var)
                    if not value:
                        raise CommandError('You must use --%s with --noinput.' % field_name)
                    field = self.UserModel._meta.get_field(field_name)
                    user_data[field_name] = field.clean(value, None)
                    if field.many_to_many and isinstance(user_data[field_name], str):
                        user_data[field_name] = [
                            pk.strip() for pk in user_data[field_name].split(',')
                        ]

            self.UserModel._default_manager.db_manager(database).create_superuser(**user_data)
            if options['verbosity'] >= 1:
                self.stdout.write("Superuser created successfully.")
        except KeyboardInterrupt:
            self.stderr.write('\nOperation cancelled.')
            sys.exit(1)
        except exceptions.ValidationError as e:
            raise CommandError('; '.join(e.messages))
        except NotRunningInTTYException:
            self.stdout.write(
                'Superuser creation skipped due to not running in a TTY. '
                'You can run `manage.py createsuperuser` in your project '
                'to create one manually.'
            )

    def get_input_data(self, field, message, default=None):
        """
        Override this method if you want to customize data inputs or
        validation exceptions.
        """
        raw_value = input(message)
        if default and raw_value == '':
            raw_value = default
        try:
            val = field.clean(raw_value, None)
        except exceptions.ValidationError as e:
            self.stderr.write("Error: %s" % '; '.join(e.messages))
            val = None

        return val

    def _get_input_message(self, field, default=None):
        return '%s%s%s: ' % (
            capfirst(field.verbose_name),
            " (leave blank to use '%s')" % default if default else '',
            ' (%s.%s)' % (
                field.remote_field.model._meta.object_name,
                field.m2m_target_field_name() if field.many_to_many else field.remote_field.field_name,
            ) if field.remote_field else '',
        )

    def _validate_username(self, username, verbose_field_name, database):
        """Validate username. If invalid, return a string error message."""
        if self.username_field.unique:
            try:
                self.UserModel._default_manager.db_manager(database).get_by_natural_key(username)
            except self.UserModel.DoesNotExist:
                pass
            else:
                return 'Error: That %s is already taken.' % verbose_field_name
        if not username:
            return '%s cannot be blank.' % capfirst(verbose_field_name)
        try:
            self.username_field.clean(username, None)
        except exceptions.ValidationError as e:
            return '; '.join(e.messages)

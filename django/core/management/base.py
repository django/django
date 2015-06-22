# -*- coding: utf-8 -*-
"""
Base classes for writing management commands (named commands which can
be executed through ``django-admin`` or ``manage.py``).
"""

from __future__ import unicode_literals

import os
import sys
import warnings
from argparse import ArgumentParser
from optparse import OptionParser

import django
from django.core import checks
from django.core.exceptions import ImproperlyConfigured
from django.core.management.color import color_style, no_style
from django.db import connections
from django.utils.deprecation import (
    RemovedInDjango19Warning, RemovedInDjango110Warning,
)
from django.utils.encoding import force_str


class CommandError(Exception):
    """
    Exception class indicating a problem while executing a management
    command.

    If this exception is raised during the execution of a management
    command, it will be caught and turned into a nicely-printed error
    message to the appropriate output stream (i.e., stderr); as a
    result, raising this exception (with a sensible description of the
    error) is the preferred way to indicate that something has gone
    wrong in the execution of a command.

    """
    pass


class SystemCheckError(CommandError):
    """
    The system check framework detected unrecoverable errors.
    """
    pass


class CommandParser(ArgumentParser):
    """
    Customized ArgumentParser class to improve some error messages and prevent
    SystemExit in several occasions, as SystemExit is unacceptable when a
    command is called programmatically.
    """
    def __init__(self, cmd, **kwargs):
        self.cmd = cmd
        super(CommandParser, self).__init__(**kwargs)

    def parse_args(self, args=None, namespace=None):
        # Catch missing argument for a better error message
        if (hasattr(self.cmd, 'missing_args_message') and
                not (args or any(not arg.startswith('-') for arg in args))):
            self.error(self.cmd.missing_args_message)
        return super(CommandParser, self).parse_args(args, namespace)

    def error(self, message):
        if self.cmd._called_from_command_line:
            super(CommandParser, self).error(message)
        else:
            raise CommandError("Error: %s" % message)


def handle_default_options(options):
    """
    Include any default options that all commands should accept here
    so that ManagementUtility can handle them before searching for
    user commands.

    """
    if options.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
    if options.pythonpath:
        sys.path.insert(0, options.pythonpath)


class OutputWrapper(object):
    """
    Wrapper around stdout/stderr
    """
    @property
    def style_func(self):
        return self._style_func

    @style_func.setter
    def style_func(self, style_func):
        if style_func and hasattr(self._out, 'isatty') and self._out.isatty():
            self._style_func = style_func
        else:
            self._style_func = lambda x: x

    def __init__(self, out, style_func=None, ending='\n'):
        self._out = out
        self.style_func = None
        self.ending = ending

    def __getattr__(self, name):
        return getattr(self._out, name)

    def write(self, msg, style_func=None, ending=None):
        ending = self.ending if ending is None else ending
        if ending and not msg.endswith(ending):
            msg += ending
        style_func = style_func or self.style_func
        self._out.write(force_str(style_func(msg)))


class BaseCommand(object):
    """
    The base class from which all management commands ultimately
    derive.

    Use this class if you want access to all of the mechanisms which
    parse the command-line arguments and work out what code to call in
    response; if you don't need to change any of that behavior,
    consider using one of the subclasses defined in this file.

    If you are interested in overriding/customizing various aspects of
    the command-parsing and -execution behavior, the normal flow works
    as follows:

    1. ``django-admin`` or ``manage.py`` loads the command class
       and calls its ``run_from_argv()`` method.

    2. The ``run_from_argv()`` method calls ``create_parser()`` to get
       an ``ArgumentParser`` for the arguments, parses them, performs
       any environment changes requested by options like
       ``pythonpath``, and then calls the ``execute()`` method,
       passing the parsed arguments.

    3. The ``execute()`` method attempts to carry out the command by
       calling the ``handle()`` method with the parsed arguments; any
       output produced by ``handle()`` will be printed to standard
       output and, if the command is intended to produce a block of
       SQL statements, will be wrapped in ``BEGIN`` and ``COMMIT``.

    4. If ``handle()`` or ``execute()`` raised any exception (e.g.
       ``CommandError``), ``run_from_argv()`` will  instead print an error
       message to ``stderr``.

    Thus, the ``handle()`` method is typically the starting point for
    subclasses; many built-in commands and command types either place
    all of their logic in ``handle()``, or perform some additional
    parsing work in ``handle()`` and then delegate from it to more
    specialized methods as needed.

    Several attributes affect behavior at various steps along the way:

    ``args``
        A string listing the arguments accepted by the command,
        suitable for use in help messages; e.g., a command which takes
        a list of application names might set this to '<app_label
        app_label ...>'.

    ``can_import_settings``
        A boolean indicating whether the command needs to be able to
        import Django settings; if ``True``, ``execute()`` will verify
        that this is possible before proceeding. Default value is
        ``True``.

    ``help``
        A short description of the command, which will be printed in
        help messages.

    ``option_list``
        This is the list of ``optparse`` options which will be fed
        into the command's ``OptionParser`` for parsing arguments.
        Deprecated and will be removed in Django 1.10.

    ``output_transaction``
        A boolean indicating whether the command outputs SQL
        statements; if ``True``, the output will automatically be
        wrapped with ``BEGIN;`` and ``COMMIT;``. Default value is
        ``False``.

    ``requires_system_checks``
        A boolean; if ``True``, entire Django project will be checked for errors
        prior to executing the command. Default value is ``True``.
        To validate an individual application's models
        rather than all applications' models, call
        ``self.check(app_configs)`` from ``handle()``, where ``app_configs``
        is the list of application's configuration provided by the
        app registry.

    ``requires_model_validation``
        DEPRECATED - This value will only be used if requires_system_checks
        has not been provided. Defining both ``requires_system_checks`` and
        ``requires_model_validation`` will result in an error.

        A boolean; if ``True``, validation of installed models will be
        performed prior to executing the command. Default value is
        ``True``. To validate an individual application's models
        rather than all applications' models, call
        ``self.validate(app_config)`` from ``handle()``, where ``app_config``
        is the application's configuration provided by the app registry.

    ``leave_locale_alone``
        A boolean indicating whether the locale set in settings should be
        preserved during the execution of the command instead of translations
        being deactivated.

        Default value is ``False``.

        Make sure you know what you are doing if you decide to change the value
        of this option in your custom command if it creates database content
        that is locale-sensitive and such content shouldn't contain any
        translations (like it happens e.g. with django.contrib.auth
        permissions) as activating any locale might cause unintended effects.

        This option can't be False when the can_import_settings option is set
        to False too because attempting to deactivate translations needs access
        to settings. This condition will generate a CommandError.
    """
    # Metadata about this command.
    option_list = ()
    help = ''
    args = ''

    # Configuration shortcuts that alter various logic.
    _called_from_command_line = False
    can_import_settings = True
    output_transaction = False  # Whether to wrap the output in a "BEGIN; COMMIT;"
    leave_locale_alone = False

    # Uncomment the following line of code after deprecation plan for
    # requires_model_validation comes to completion:
    #
    # requires_system_checks = True

    def __init__(self, stdout=None, stderr=None, no_color=False):
        self.stdout = OutputWrapper(stdout or sys.stdout)
        self.stderr = OutputWrapper(stderr or sys.stderr)
        if no_color:
            self.style = no_style()
        else:
            self.style = color_style()
            self.stderr.style_func = self.style.ERROR

        # `requires_model_validation` is deprecated in favor of
        # `requires_system_checks`. If both options are present, an error is
        # raised. Otherwise the present option is used. If none of them is
        # defined, the default value (True) is used.
        has_old_option = hasattr(self, 'requires_model_validation')
        has_new_option = hasattr(self, 'requires_system_checks')

        if has_old_option:
            warnings.warn(
                '"requires_model_validation" is deprecated '
                'in favor of "requires_system_checks".',
                RemovedInDjango19Warning)
        if has_old_option and has_new_option:
            raise ImproperlyConfigured(
                'Command %s defines both "requires_model_validation" '
                'and "requires_system_checks", which is illegal. Use only '
                '"requires_system_checks".' % self.__class__.__name__)

        self.requires_system_checks = (
            self.requires_system_checks if has_new_option else
            self.requires_model_validation if has_old_option else
            True)

    @property
    def use_argparse(self):
        return not bool(self.option_list)

    def get_version(self):
        """
        Return the Django version, which should be correct for all
        built-in Django commands. User-supplied commands should
        override this method.

        """
        return django.get_version()

    def usage(self, subcommand):
        """
        Return a brief description of how to use this command, by
        default from the attribute ``self.help``.

        """
        usage = '%%prog %s [options] %s' % (subcommand, self.args)
        if self.help:
            return '%s\n\n%s' % (usage, self.help)
        else:
            return usage

    def create_parser(self, prog_name, subcommand):
        """
        Create and return the ``ArgumentParser`` which will be used to
        parse the arguments to this command.

        """
        if not self.use_argparse:
            def store_as_int(option, opt_str, value, parser):
                setattr(parser.values, option.dest, int(value))

            # Backwards compatibility: use deprecated optparse module
            warnings.warn("OptionParser usage for Django management commands "
                          "is deprecated, use ArgumentParser instead",
                          RemovedInDjango110Warning)
            parser = OptionParser(prog=prog_name,
                                usage=self.usage(subcommand),
                                version=self.get_version())
            parser.add_option('-v', '--verbosity', action='callback', dest='verbosity', default=1,
                type='choice', choices=['0', '1', '2', '3'], callback=store_as_int,
                help='Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 3=very verbose output')
            parser.add_option('--settings',
                help=(
                    'The Python path to a settings module, e.g. '
                    '"myproject.settings.main". If this isn\'t provided, the '
                    'DJANGO_SETTINGS_MODULE environment variable will be used.'
                ),
            )
            parser.add_option('--pythonpath',
                help='A directory to add to the Python path, e.g. "/home/djangoprojects/myproject".'),
            parser.add_option('--traceback', action='store_true',
                help='Raise on CommandError exceptions')
            parser.add_option('--no-color', action='store_true', dest='no_color', default=False,
                help="Don't colorize the command output.")
            for opt in self.option_list:
                parser.add_option(opt)
        else:
            parser = CommandParser(self, prog="%s %s" % (os.path.basename(prog_name), subcommand),
                description=self.help or None)
            parser.add_argument('--version', action='version', version=self.get_version())
            parser.add_argument('-v', '--verbosity', action='store', dest='verbosity', default='1',
                type=int, choices=[0, 1, 2, 3],
                help='Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 3=very verbose output')
            parser.add_argument('--settings',
                help=(
                    'The Python path to a settings module, e.g. '
                    '"myproject.settings.main". If this isn\'t provided, the '
                    'DJANGO_SETTINGS_MODULE environment variable will be used.'
                ),
            )
            parser.add_argument('--pythonpath',
                help='A directory to add to the Python path, e.g. "/home/djangoprojects/myproject".')
            parser.add_argument('--traceback', action='store_true',
                help='Raise on CommandError exceptions')
            parser.add_argument('--no-color', action='store_true', dest='no_color', default=False,
                help="Don't colorize the command output.")
            if self.args:
                # Keep compatibility and always accept positional arguments, like optparse when args is set
                parser.add_argument('args', nargs='*')
            self.add_arguments(parser)
        return parser

    def add_arguments(self, parser):
        """
        Entry point for subclassed commands to add custom arguments.
        """
        pass

    def print_help(self, prog_name, subcommand):
        """
        Print the help message for this command, derived from
        ``self.usage()``.

        """
        parser = self.create_parser(prog_name, subcommand)
        parser.print_help()

    def run_from_argv(self, argv):
        """
        Set up any environment changes requested (e.g., Python path
        and Django settings), then run this command. If the
        command raises a ``CommandError``, intercept it and print it sensibly
        to stderr. If the ``--traceback`` option is present or the raised
        ``Exception`` is not ``CommandError``, raise it.
        """
        self._called_from_command_line = True
        parser = self.create_parser(argv[0], argv[1])

        if self.use_argparse:
            options = parser.parse_args(argv[2:])
            cmd_options = vars(options)
            # Move positional args out of options to mimic legacy optparse
            args = cmd_options.pop('args', ())
        else:
            options, args = parser.parse_args(argv[2:])
            cmd_options = vars(options)
        handle_default_options(options)
        try:
            self.execute(*args, **cmd_options)
        except Exception as e:
            if options.traceback or not isinstance(e, CommandError):
                raise

            # SystemCheckError takes care of its own formatting.
            if isinstance(e, SystemCheckError):
                self.stderr.write(str(e), lambda x: x)
            else:
                self.stderr.write('%s: %s' % (e.__class__.__name__, e))
            sys.exit(1)
        finally:
            connections.close_all()

    def execute(self, *args, **options):
        """
        Try to execute this command, performing system checks if needed (as
        controlled by attributes ``self.requires_system_checks`` and
        ``self.requires_model_validation``, except if force-skipped).
        """
        if options.get('no_color'):
            self.style = no_style()
            self.stderr.style_func = None
        if options.get('stdout'):
            self.stdout = OutputWrapper(options['stdout'])
        if options.get('stderr'):
            self.stderr = OutputWrapper(options.get('stderr'), self.stderr.style_func)

        saved_locale = None
        if not self.leave_locale_alone:
            # Only mess with locales if we can assume we have a working
            # settings file, because django.utils.translation requires settings
            # (The final saying about whether the i18n machinery is active will be
            # found in the value of the USE_I18N setting)
            if not self.can_import_settings:
                raise CommandError("Incompatible values of 'leave_locale_alone' "
                                   "(%s) and 'can_import_settings' (%s) command "
                                   "options." % (self.leave_locale_alone,
                                                 self.can_import_settings))
            # Deactivate translations, because django-admin creates database
            # content like permissions, and those shouldn't contain any
            # translations.
            from django.utils import translation
            saved_locale = translation.get_language()
            translation.deactivate_all()

        try:
            if (self.requires_system_checks and
                    not options.get('skip_validation') and  # Remove at the end of deprecation for `skip_validation`.
                    not options.get('skip_checks')):
                self.check()
            output = self.handle(*args, **options)
            if output:
                if self.output_transaction:
                    # This needs to be imported here, because it relies on
                    # settings.
                    from django.db import connections, DEFAULT_DB_ALIAS
                    connection = connections[options.get('database', DEFAULT_DB_ALIAS)]
                    if connection.ops.start_transaction_sql():
                        self.stdout.write(self.style.SQL_KEYWORD(connection.ops.start_transaction_sql()))
                self.stdout.write(output)
                if self.output_transaction:
                    self.stdout.write('\n' + self.style.SQL_KEYWORD(connection.ops.end_transaction_sql()))
        finally:
            if saved_locale is not None:
                translation.activate(saved_locale)

    def validate(self, app_config=None, display_num_errors=False):
        """ Deprecated. Delegates to ``check``."""

        if app_config is None:
            app_configs = None
        else:
            app_configs = [app_config]

        return self.check(app_configs=app_configs, display_num_errors=display_num_errors)

    def check(self, app_configs=None, tags=None, display_num_errors=False,
              include_deployment_checks=False):
        """
        Uses the system check framework to validate entire Django project.
        Raises CommandError for any serious message (error or critical errors).
        If there are only light messages (like warnings), they are printed to
        stderr and no exception is raised.
        """
        all_issues = checks.run_checks(
            app_configs=app_configs,
            tags=tags,
            include_deployment_checks=include_deployment_checks,
        )

        header, body, footer = "", "", ""
        visible_issue_count = 0  # excludes silenced warnings

        if all_issues:
            debugs = [e for e in all_issues if e.level < checks.INFO and not e.is_silenced()]
            infos = [e for e in all_issues if checks.INFO <= e.level < checks.WARNING and not e.is_silenced()]
            warnings = [e for e in all_issues if checks.WARNING <= e.level < checks.ERROR and not e.is_silenced()]
            errors = [e for e in all_issues if checks.ERROR <= e.level < checks.CRITICAL]
            criticals = [e for e in all_issues if checks.CRITICAL <= e.level]
            sorted_issues = [
                (criticals, 'CRITICALS'),
                (errors, 'ERRORS'),
                (warnings, 'WARNINGS'),
                (infos, 'INFOS'),
                (debugs, 'DEBUGS'),
            ]

            for issues, group_name in sorted_issues:
                if issues:
                    visible_issue_count += len(issues)
                    formatted = (
                        self.style.ERROR(force_str(e))
                        if e.is_serious()
                        else self.style.WARNING(force_str(e))
                        for e in issues)
                    formatted = "\n".join(sorted(formatted))
                    body += '\n%s:\n%s\n' % (group_name, formatted)

        if visible_issue_count:
            header = "System check identified some issues:\n"

        if display_num_errors:
            if visible_issue_count:
                footer += '\n'
            footer += "System check identified %s (%s silenced)." % (
                "no issues" if visible_issue_count == 0 else
                "1 issue" if visible_issue_count == 1 else
                "%s issues" % visible_issue_count,
                len(all_issues) - visible_issue_count,
            )

        if any(e.is_serious() and not e.is_silenced() for e in all_issues):
            msg = self.style.ERROR("SystemCheckError: %s" % header) + body + footer
            raise SystemCheckError(msg)
        else:
            msg = header + body + footer

        if msg:
            if visible_issue_count:
                self.stderr.write(msg, lambda x: x)
            else:
                self.stdout.write(msg)

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.

        """
        raise NotImplementedError('subclasses of BaseCommand must provide a handle() method')


class AppCommand(BaseCommand):
    """
    A management command which takes one or more installed application labels
    as arguments, and does something with each of them.

    Rather than implementing ``handle()``, subclasses must implement
    ``handle_app_config()``, which will be called once for each application.
    """
    missing_args_message = "Enter at least one application label."

    def add_arguments(self, parser):
        parser.add_argument('args', metavar='app_label', nargs='+',
            help='One or more application label.')

    def handle(self, *app_labels, **options):
        from django.apps import apps
        try:
            app_configs = [apps.get_app_config(app_label) for app_label in app_labels]
        except (LookupError, ImportError) as e:
            raise CommandError("%s. Are you sure your INSTALLED_APPS setting is correct?" % e)
        output = []
        for app_config in app_configs:
            app_output = self.handle_app_config(app_config, **options)
            if app_output:
                output.append(app_output)
        return '\n'.join(output)

    def handle_app_config(self, app_config, **options):
        """
        Perform the command's actions for app_config, an AppConfig instance
        corresponding to an application label given on the command line.
        """
        try:
            # During the deprecation path, keep delegating to handle_app if
            # handle_app_config isn't implemented in a subclass.
            handle_app = self.handle_app
        except AttributeError:
            # Keep only this exception when the deprecation completes.
            raise NotImplementedError(
                "Subclasses of AppCommand must provide"
                "a handle_app_config() method.")
        else:
            warnings.warn(
                "AppCommand.handle_app() is superseded by "
                "AppCommand.handle_app_config().",
                RemovedInDjango19Warning, stacklevel=2)
            if app_config.models_module is None:
                raise CommandError(
                    "AppCommand cannot handle app '%s' in legacy mode "
                    "because it doesn't have a models module."
                    % app_config.label)
            return handle_app(app_config.models_module, **options)


class LabelCommand(BaseCommand):
    """
    A management command which takes one or more arbitrary arguments
    (labels) on the command line, and does something with each of
    them.

    Rather than implementing ``handle()``, subclasses must implement
    ``handle_label()``, which will be called once for each label.

    If the arguments should be names of installed applications, use
    ``AppCommand`` instead.

    """
    label = 'label'
    missing_args_message = "Enter at least one %s." % label

    def add_arguments(self, parser):
        parser.add_argument('args', metavar=self.label, nargs='+')

    def handle(self, *labels, **options):
        output = []
        for label in labels:
            label_output = self.handle_label(label, **options)
            if label_output:
                output.append(label_output)
        return '\n'.join(output)

    def handle_label(self, label, **options):
        """
        Perform the command's actions for ``label``, which will be the
        string as given on the command line.

        """
        raise NotImplementedError('subclasses of LabelCommand must provide a handle_label() method')


class NoArgsCommand(BaseCommand):
    """
    A command which takes no arguments on the command line.

    Rather than implementing ``handle()``, subclasses must implement
    ``handle_noargs()``; ``handle()`` itself is overridden to ensure
    no arguments are passed to the command.

    Attempting to pass arguments will raise ``CommandError``.

    """
    args = ''

    def __init__(self):
        warnings.warn(
            "NoArgsCommand class is deprecated and will be removed in Django 1.10. "
            "Use BaseCommand instead, which takes no arguments by default.",
            RemovedInDjango110Warning
        )
        super(NoArgsCommand, self).__init__()

    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")
        return self.handle_noargs(**options)

    def handle_noargs(self, **options):
        """
        Perform this command's actions.

        """
        raise NotImplementedError('subclasses of NoArgsCommand must provide a handle_noargs() method')

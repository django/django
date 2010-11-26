from optparse import make_option
import os
import re
import sys
import socket

from django.core.management.base import BaseCommand, CommandError
from django.core.handlers.wsgi import WSGIHandler
from django.core.servers.basehttp import AdminMediaHandler, run, WSGIServerException
from django.utils import autoreload

naiveip_re = r'^(?:(?P<addr>\d{1,3}(?:\.\d{1,3}){3}|\[[a-fA-F0-9:]+\]):)?(?P<port>\d+)$'
DEFAULT_PORT = "8000"

class BaseRunserverCommand(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--ipv6', '-6', action='store_true', dest='use_ipv6', default=False,
            help='Tells Django to use a IPv6 address.'),
        make_option('--noreload', action='store_false', dest='use_reloader', default=True,
            help='Tells Django to NOT use the auto-reloader.'),
    )
    help = "Starts a lightweight Web server for development."
    args = '[optional port number, or ipaddr:port]'

    # Validation is called explicitly each time the server is reloaded.
    requires_model_validation = False

    def get_handler(self, *args, **options):
        """
        Returns the default WSGI handler for the runner.
        """
        return WSGIHandler()

    def handle(self, addrport='', *args, **options):
        self.use_ipv6 = options.get('use_ipv6')
        if self.use_ipv6 and not hasattr(socket, 'AF_INET6'):
            raise CommandError('Your Python does not support IPv6.')
        if args:
            raise CommandError('Usage is runserver %s' % self.args)
        if not addrport:
            self.addr = ''
            self.port = DEFAULT_PORT
        else:
            m = re.match(naiveip_re, addrport)
            if m is None:
                raise CommandError('%r is not a valid port number'
                                   'or address:port pair.' % addrport)
            self.addr, self.port = m.groups()
            if not self.port.isdigit():
                raise CommandError("%r is not a valid port number." % self.port)
            if self.addr:
                if self.addr.startswith('[') and self.addr.endswith(']'):
                    self.addr = self.addr[1:-1]
                    self.use_ipv6 = True
                elif self.use_ipv6:
                    raise CommandError('IPv6 addresses must be surrounded '
                                       'with brackets, e.g. [::1].')
        if not self.addr:
            self.addr = self.use_ipv6 and '::1' or '127.0.0.1'
        self.run(*args, **options)

    def run(self, *args, **options):
        """
        Runs the server, using the autoreloader if needed
        """
        use_reloader = options.get('use_reloader', True)

        if use_reloader:
            autoreload.main(self.inner_run, args, options)
        else:
            self.inner_run(*args, **options)

    def inner_run(self, *args, **options):
        from django.conf import settings
        from django.utils import translation

        shutdown_message = options.get('shutdown_message', '')
        quit_command = (sys.platform == 'win32') and 'CTRL-BREAK' or 'CONTROL-C'

        self.stdout.write("Validating models...\n\n")
        self.validate(display_num_errors=True)
        self.stdout.write((
            "Django version %(version)s, using settings %(settings)r\n"
            "Development server is running at http://%(addr)s:%(port)s/\n"
            "Quit the server with %(quit_command)s.\n"
        ) % {
            "version": self.get_version(),
            "settings": settings.SETTINGS_MODULE,
            "addr": self.use_ipv6 and '[%s]' % self.addr or self.addr,
            "port": self.port,
            "quit_command": quit_command,
        })
        # django.core.management.base forces the locale to en-us. We should
        # set it up correctly for the first request (particularly important
        # in the "--noreload" case).
        translation.activate(settings.LANGUAGE_CODE)

        try:
            handler = self.get_handler(*args, **options)
            run(self.addr, int(self.port), handler, ipv6=self.use_ipv6)
        except WSGIServerException, e:
            # Use helpful error messages instead of ugly tracebacks.
            ERRORS = {
                13: "You don't have permission to access that port.",
                98: "That port is already in use.",
                99: "That IP address can't be assigned-to.",
            }
            try:
                error_text = ERRORS[e.args[0].args[0]]
            except (AttributeError, KeyError):
                error_text = str(e)
            sys.stderr.write(self.style.ERROR("Error: %s" % error_text) + '\n')
            # Need to use an OS exit because sys.exit doesn't work in a thread
            os._exit(1)
        except KeyboardInterrupt:
            if shutdown_message:
                self.stdout.write("%s\n" % shutdown_message)
            sys.exit(0)

class Command(BaseRunserverCommand):
    option_list = BaseRunserverCommand.option_list + (
        make_option('--adminmedia', dest='admin_media_path', default='',
            help='Specifies the directory from which to serve admin media.'),
    )

    def get_handler(self, *args, **options):
        """
        Serves admin media like old-school (deprecation pending).
        """
        handler = super(Command, self).get_handler(*args, **options)
        return AdminMediaHandler(handler, options.get('admin_media_path', ''))

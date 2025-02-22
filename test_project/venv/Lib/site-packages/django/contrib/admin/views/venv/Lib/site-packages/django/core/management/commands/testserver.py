from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Runs a development server with data from the given fixture(s)."

    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "args",
            metavar="fixture",
            nargs="*",
            help="Path(s) to fixtures to load before running the server.",
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Tells Django to NOT prompt the user for input of any kind.",
        )
        parser.add_argument(
            "--addrport",
            default="",
            help="Port number or ipaddr:port to run the server on.",
        )
        parser.add_argument(
            "--ipv6",
            "-6",
            action="store_true",
            dest="use_ipv6",
            help="Tells Django to use an IPv6 address.",
        )

    def handle(self, *fixture_labels, **options):
        verbosity = options["verbosity"]
        interactive = options["interactive"]

        # Create a test database.
        db_name = connection.creation.create_test_db(
            verbosity=verbosity, autoclobber=not interactive, serialize=False
        )

        # Import the fixture data into the test database.
        call_command("loaddata", *fixture_labels, verbosity=verbosity)

        # Run the development server. Turn off auto-reloading because it causes
        # a strange error -- it causes this handle() method to be called
        # multiple times.
        shutdown_message = (
            "\nServer stopped.\nNote that the test database, %r, has not been "
            "deleted. You can explore it on your own." % db_name
        )
        use_threading = connection.features.test_db_allows_multiple_connections
        call_command(
            "runserver",
            addrport=options["addrport"],
            shutdown_message=shutdown_message,
            use_reloader=False,
            use_ipv6=options["use_ipv6"],
            use_threading=use_threading,
        )

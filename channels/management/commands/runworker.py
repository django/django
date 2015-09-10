import time
from wsgiref.simple_server import BaseHTTPRequestHandler
from django.core.management import BaseCommand, CommandError
from channels import channel_backends, DEFAULT_CHANNEL_BACKEND
from channels.worker import Worker


class Command(BaseCommand):

    def handle(self, *args, **options):
        # Get the backend to use
        channel_backend = channel_backends[DEFAULT_CHANNEL_BACKEND]
        if channel_backend.local_only:
            raise CommandError(
                "You have a process-local channel backend configured, and so cannot run separate workers.\n"
                "Configure a network-based backend in CHANNEL_BACKENDS to use this command."
            )
        # Launch a worker
        self.stdout.write("Running worker against backend %s" % channel_backend)
        # Optionally provide an output callback
        callback = None
        if options.get("verbosity", 1) > 1:
            callback = self.consumer_called
        # Run the worker
        try:
            Worker(channel_backend=channel_backend, callback=callback).run()
        except KeyboardInterrupt:
            pass

    def consumer_called(self, channel, message):
        self.stdout.write("[%s] %s" % (self.log_date_time_string(), channel))

    def log_date_time_string(self):
        """Return the current time formatted for logging."""
        now = time.time()
        year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
        s = "%02d/%3s/%04d %02d:%02d:%02d" % (
                day, BaseHTTPRequestHandler.monthname[month], year, hh, mm, ss)
        return s

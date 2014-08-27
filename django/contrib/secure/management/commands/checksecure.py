import textwrap

from django.core.management.base import NoArgsCommand
from django.utils.termcolors import make_style

from ...check import get_check
from ...conf import conf


class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        verbosity = int(options.get("verbosity"))

        self.style.SUCCESS = make_style(opts=('bold',), fg='green')

        warn_count = 0

        for func_path in conf.SECURE_CHECKS:
            func = get_check(func_path)

            if verbosity:
                self.stdout.write("Running %s... " % func_path)

            messages = []
            for warn_code in func():
                if verbosity:
                    msg = getattr(func, "messages", {}).get(
                        warn_code, warn_code)
                else:
                    msg = warn_code
                messages.append(msg)

            if verbosity:
                if messages:
                    self.stdout.write(self.style.ERROR("FAIL"))
                else:
                    self.stdout.write(self.style.SUCCESS("OK"))
                self.stdout.write("\n")

            for msg in messages:
                self.stderr.write(self.style.ERROR(textwrap.fill(msg)) + "\n")
                if verbosity:
                    self.stderr.write("\n")

            warn_count += len(messages)

        if verbosity and not warn_count:
            self.stdout.write(self.style.SUCCESS("\nAll clear!\n\n"))

from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument('--format-json', action='store_true', dest='format_json')
        group.add_argument('--format-xml', action='store_true', dest='format_xml')

    def handle(self, *args, **options):
        self.stdout.write(f"format_json={options['format_json']}, format_xml={options['format_xml']}")

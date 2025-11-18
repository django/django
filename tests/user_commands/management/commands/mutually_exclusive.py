from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--shop-id', nargs='?', type=int, default=None, dest='shop_id')
        group.add_argument('--shop', nargs='?', type=str, default=None, dest='shop_name')

    def handle(self, *args, **options):
        self.stdout.write(f"shop_id={options['shop_id']}, shop_name={options['shop_name']}")

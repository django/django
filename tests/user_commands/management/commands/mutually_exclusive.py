from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def add_arguments(self, parser):
        shop = parser.add_mutually_exclusive_group(required=True)
        shop.add_argument('--shop-id', nargs='?', type=int, default=None, dest='shop_id')
        shop.add_argument('--shop', nargs='?', type=str, default=None, dest='shop_name')

    def handle(self, *args, **options):
        self.stdout.write(','.join(str(options.get(key)) for key in ['shop_id', 'shop_name']))

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Enter a transaction"
    args = ''

    def handle(self, *args, **options):
        transaction.enter_transaction_management()

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Validates all installed models."

    requires_model_validation = False

    def handle(self, **options):
        self.validate()

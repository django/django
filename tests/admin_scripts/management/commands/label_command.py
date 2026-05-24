import logging
logger = logging.getLogger(__name__)
from django.core.management.base import LabelCommand


class Command(LabelCommand):
    help = "Test Label-based commands"
    requires_system_checks = []

    def handle_label(self, label, **options):
        logger.info(
            "EXECUTE:LabelCommand label=%s, options=%s"
            % (label, sorted(options.items()))
        )

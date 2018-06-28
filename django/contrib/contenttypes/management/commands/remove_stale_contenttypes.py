from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand
from django.db import DEFAULT_DB_ALIAS, router
from django.db.models.deletion import Collector

from ...management import get_contenttypes_and_models


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput', '--no-input', action='store_false', dest='interactive',
            help='Tells Django to NOT prompt the user for input of any kind.',
        )
        parser.add_argument(
            '--database', action='store', dest='database', default=DEFAULT_DB_ALIAS,
            help='Nominates the database to use. Defaults to the "default" database.',
        )

    def handle(self, **options):
        db = options['database']
        interactive = options['interactive']
        verbosity = options['verbosity']

        for app_config in apps.get_app_configs():
            content_types, app_models = get_contenttypes_and_models(app_config, db, ContentType)
            to_remove = [
                ct for (model_name, ct) in content_types.items()
                if model_name not in app_models
            ]
            # Confirm that the content type is stale before deletion.
            using = router.db_for_write(ContentType)
            if to_remove:
                if interactive:
                    ct_info = []
                    for ct in to_remove:
                        ct_info.append('    - Content type for %s.%s' % (ct.app_label, ct.model))
                        collector = NoFastDeleteCollector(using=using)
                        collector.collect([ct])

                        for obj_type, objs in collector.data.items():
                            if objs != {ct}:
                                ct_info.append('    - %s %s object(s)' % (
                                    len(objs),
                                    obj_type._meta.label,
                                ))
                    content_type_display = '\n'.join(ct_info)
                    self.stdout.write("""Some content types in your database are stale and can be deleted.
Any objects that depend on these content types will also be deleted.
The content types and dependent objects that would be deleted are:

%s

This list doesn't include any cascade deletions to data outside of Django's
models (uncommon).

Are you sure you want to delete these content types?
If you're unsure, answer 'no'.\n""" % content_type_display)
                    ok_to_delete = input("Type 'yes' to continue, or 'no' to cancel: ")
                else:
                    ok_to_delete = False

                if ok_to_delete == 'yes':
                    for ct in to_remove:
                        if verbosity >= 2:
                            self.stdout.write("Deleting stale content type '%s | %s'" % (ct.app_label, ct.model))
                        ct.delete()
                else:
                    if verbosity >= 2:
                        self.stdout.write("Stale content types remain.")


class NoFastDeleteCollector(Collector):
    def can_fast_delete(self, *args, **kwargs):
        """
        Always load related objects to display them when showing confirmation.
        """
        return False

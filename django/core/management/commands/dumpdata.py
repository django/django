from django.core.management.base import BaseCommand, CommandError
from django.core import serializers

from optparse import make_option

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--format', default='json', dest='format',
            help='Specifies the output serialization format for fixtures.'),
        make_option('--indent', default=None, dest='indent', type='int',
            help='Specifies the indent level to use when pretty-printing output'),
    )
    help = 'Output the contents of the database as a fixture of the given format.'
    args = '[appname ...]'

    def handle(self, *app_labels, **options):
        from django.db.models import get_app, get_apps, get_models

        format = options.get('format', 'json')
        indent = options.get('indent', None)
        show_traceback = options.get('traceback', False)

        if len(app_labels) == 0:
            app_list = get_apps()
        else:
            app_list = [get_app(app_label) for app_label in app_labels]

        # Check that the serialization format exists; this is a shortcut to
        # avoid collating all the objects and _then_ failing.
        if format not in serializers.get_public_serializer_formats():
            raise CommandError("Unknown serialization format: %s" % format)

        try:
            serializers.get_serializer(format)
        except KeyError:
            raise CommandError("Unknown serialization format: %s" % format)

        objects = []
        for app in app_list:
            for model in get_models(app):
                objects.extend(model._default_manager.all())
        try:
            return serializers.serialize(format, objects, indent=indent)
        except Exception, e:
            if show_traceback:
                raise
            raise CommandError("Unable to serialize database: %s" % e)

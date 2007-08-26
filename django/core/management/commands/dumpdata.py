from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Output the contents of the database as a fixture of the given format.'
    args = '[--format] [--indent] [appname ...]'

    def handle(self, *app_labels, **options):
        from django.db.models import get_app, get_apps, get_models
        from django.core import serializers

        format = options.get('format', 'json')
        indent = options.get('indent', None)

        if len(app_labels) == 0:
            app_list = get_apps()
        else:
            app_list = [get_app(app_label) for app_label in app_labels]

        # Check that the serialization format exists; this is a shortcut to
        # avoid collating all the objects and _then_ failing.
        try:
            serializers.get_serializer(format)
        except KeyError:
            raise CommandError("Unknown serialization format: %s" % format)

        objects = []
        for app in app_list:
            for model in get_models(app):
                objects.extend(model.objects.all())
        try:
            return serializers.serialize(format, objects, indent=indent)
        except Exception, e:
            raise CommandError("Unable to serialize database: %s" % e)

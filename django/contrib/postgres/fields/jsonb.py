from django.db.models import JSONField as BuiltinJSONField

__all__ = ['JSONField']


class JSONField(BuiltinJSONField):
    system_check_deprecated_details = {
        'msg': (
            'django.contrib.postgres.fields.JSONField is deprecated '
            'and will be removed in Django 4.0.'
        ),
        'hint': 'Use django.db.models.JSONField instead.',
        'id': 'fields.W903'
    }

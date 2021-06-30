from mango.db.models import JSONField as BuiltinJSONField

__all__ = ['JSONField']


class JSONField(BuiltinJSONField):
    system_check_removed_details = {
        'msg': (
            'mango.contrib.postgres.fields.JSONField is removed except for '
            'support in historical migrations.'
        ),
        'hint': 'Use mango.db.models.JSONField instead.',
        'id': 'fields.E904',
    }

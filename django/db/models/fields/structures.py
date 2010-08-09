from django.core.exceptions import ValidationError
from django.db.models.loading import cache
from django.db.models.fields import Field
from django.db.models.fields.subclassing import SubfieldBase


class ListField(Field):
    __metaclass__ = SubfieldBase
    
    def __init__(self, field_type):
        self.field_type = field_type
        super(ListField, self).__init__(default=[])
    
    def get_prep_lookup(self, lookup_type, value):
        return self.field_type.get_prep_lookup(lookup_type, value)
    
    def get_db_prep_save(self, value, connection):
        return [
            self.field_type.get_db_prep_save(o, connection=connection)
            for o in value
        ]
    
    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        return self.field_type.get_db_prep_lookup(
            lookup_type, value, connection=connection, prepared=prepared
        )
    
    def to_python(self, value):
        try:
            value = iter(value)
        except TypeError:
            raise ValidationError("Value should be iterable")
        return [
            self.field_type.to_python(v)
            for v in value
        ]


class EmbeddedModel(Field):
    __metaclass__ = SubfieldBase
    
    def __init__(self, to):
        self.to = to
        super(EmbeddedModel, self).__init__()
    
    def get_db_prep_save(self, value, connection):
        data = {}
        if not isinstance(value, self.to):
            raise ValidationError("Value must be an instance of %s, got %s "
                "instead" % (self.to, value))
        if type(value) is not self.to:
            data["_cls"] = (value._meta.app_label, value._meta.object_name)
        for field in value._meta.fields:
            # If the field is a OneToOneField that makes the inheritance link,
            # ignore it.
            if field.rel and field.rel.parent_link:
                continue
            data[field.column] = field.get_db_prep_save(
                getattr(value, field.name), connection=connection
            )
        return data
    
    def to_python(self, value):
        if isinstance(value, self.to):
            return value
        try:
            value = dict(value)
        except TypeError:
            raise ValidationError("Value should be a dict")
        
        if "_cls" in value:
            cls = cache.get_model(*value.pop("_cls"))
        else:
            cls = self.to
        
        return cls(**value)

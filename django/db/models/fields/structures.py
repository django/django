from django.db.models.fields import Field


class ListField(Field):
    def __init__(self, field_type):
        self.field_type = field_type
        super(ListField, self).__init__()
    
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

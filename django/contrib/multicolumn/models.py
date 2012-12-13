from django.db import models

class ForeignKeyEx(models.ForeignKey):

    include_related = [] 

    def __init__(self, *args, **kwargs):
        self.include_related = kwargs.pop('include_related', [])
        super(ForeignKeyEx, self).__init__(*args, **kwargs)

    @property
    def extra_related_fields(self):
        extra_fields = []
        for lh_field_name, rh_field_name in self.include_related:
            extra_fields.append((
                self.opts.get_field_by_name(lh_field_name)[0],
                self.rel.to._meta.get_field_by_name(rh_field_name)[0]))
        return extra_fields

    def get_related_fields(self):
        standard_related_fields = super(ForeignKeyEx, self).get_related_fields()
        return standard_related_fields + self.extra_related_fields

from django import test

from django.db.models.fields.related import ManyToManyRel

from .models import (
    Person, Quartet, Group, Reporter, Musician,
    SuperData,
    SuperM2MModel,
    RelatedModel
)


class OptionsBaseTests(test.TestCase):
    pass


class DataTests(OptionsBaseTests):

    def test_local_fields(self):
        fields = SuperData._meta.local_fields
        self.assertEquals([f.attname for f in fields], [
            'data_ptr_id',
            'name_super_data',
            'surname_super_data',
            'origin_super_data'
        ])
        self.assertTrue(all([f.rel is None or not isinstance(f.rel, ManyToManyRel)
                             for f in fields]))

    def test_local_concrete_fields(self):
        fields = SuperData._meta.local_concrete_fields
        self.assertEquals([f.attname for f in fields], [
            u'data_ptr_id',
            'name_super_data',
            'surname_super_data'
        ])
        self.assertTrue(all([f.column is not None
                             for f in fields]))

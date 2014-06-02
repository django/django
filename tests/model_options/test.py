from django import test

from django.db.models.fields.related import ManyToManyRel

from .models import (
    Person, Quartet, Group, Reporter, Musician,
    SuperData, M2MModel,
    SuperM2MModel,
    RelatedModel, BaseRelatedModel
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

    def test_many_to_many(self):
        fields = SuperM2MModel._meta.many_to_many
        self.assertEquals([f.attname for f in fields], [
            'members',
            'members_super'
        ])
        self.assertTrue(all([isinstance(f.rel, ManyToManyRel)
                             for f in fields]))

    def test_many_to_many_with_model(self):
        models = dict(SuperM2MModel._meta.get_m2m_with_model()).values()
        self.assertEquals(len(models), 2)
        self.assertEquals(models[0], M2MModel)
        self.assertEquals(models[1], None)

    def test_related_objects(self):
        objects = RelatedModel._meta.get_all_related_objects_with_model()
        fields, models = dict(objects).keys(), dict(objects).values()
        self.assertEquals([f.name for f in fields], [
            'model_options:secondrelatingobject',
            'model_options:firstrelatingobject',
        ])
        self.assertEquals(models, [
            None, BaseRelatedModel
        ])

    def test_related_objects_local(self):
        objects = RelatedModel._meta.get_all_related_objects_with_model(
            local_only=True)
        fields, models = dict(objects).keys(), dict(objects).values()
        self.assertEquals([f.name for f in fields], [
            'model_options:secondrelatingobject'
        ])
        self.assertEquals(models, [None])

    def test_related_objects_include_hidden(self):
        objects = RelatedModel._meta.get_all_related_objects_with_model(
            include_hidden=True)
        fields, models = dict(objects).keys(), dict(objects).values()
        self.assertEquals([f.name for f in fields], [
            'model_options:secondrelatingobject',
            'model_options:secondrelatinghiddenobject',
            'model_options:firstrelatingobject',
            'model_options:firstrelatinghiddenobject'
        ])
        self.assertEquals(models, [None, None, BaseRelatedModel,
                                   BaseRelatedModel])

    def test_related_objects_include_hidden_local_only(self):
        objects = RelatedModel._meta.get_all_related_objects_with_model(
            include_hidden=True, local_only=True)
        fields, models = dict(objects).keys(), dict(objects).values()
        self.assertEquals([f.name for f in fields], [
            'model_options:secondrelatingobject',
            'model_options:secondrelatinghiddenobject'
        ])
        self.assertEquals(models, [None, None])

    def test_related_objects_proxy(self):
        objects = RelatedModel._meta.get_all_related_objects_with_model(
            include_proxy_eq=True)
        fields, models = dict(objects).keys(), dict(objects).values()
        self.assertEquals([f.name for f in fields], [
            'model_options:secondrelatingobject',
            'model_options:firstrelatingobject',
            'model_options:relatingobjecttoproxy'
        ])
        self.assertEquals(models, [None, BaseRelatedModel, None])

    def test_related_objects_proxy_hidden(self):
        objects = RelatedModel._meta.get_all_related_objects_with_model(
            include_proxy_eq=True, include_hidden=True)
        fields, models = dict(objects).keys(), dict(objects).values()
        self.assertEquals([f.name for f in fields], [
            'model_options:relatingobjecttoproxy',
            'model_options:relatinghiddenobjecttoproxy',
            'model_options:firstrelatinghiddenobject',
            'model_options:firstrelatingobject',
            'model_options:secondrelatingobject',
            'model_options:secondrelatinghiddenobject'
        ])
        self.assertEquals(models, [None, None, BaseRelatedModel,
                                   BaseRelatedModel, None, None])

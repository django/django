from django import test

from django.db.models.fields.related import ManyToManyRel

from .models import (
    Person, Quartet, Group, Reporter, Musician,
    SuperData, M2MModel,
    SuperM2MModel,
    RelatedModel, BaseRelatedModel
)


class OptionsBaseTests(test.TestCase):
    def eq_field_names_and_models(self, objects, names_eq, models_eq):
        fields, models = dict(objects).keys(), dict(objects).values()
        self.assertEquals([f.name for f in fields], names_eq)
        self.assertEquals(models, models_eq)


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
        self.eq_field_names_and_models(objects, [
            'model_options:firstrelatingobject',
            'model_options:secondrelatingobject',
        ], [BaseRelatedModel, None])

    def test_related_objects_local(self):
        objects = RelatedModel._meta.get_all_related_objects_with_model(
            local_only=True)
        self.eq_field_names_and_models(objects, [
            'model_options:secondrelatingobject'
        ], [None])

    def test_related_objects_include_hidden(self):
        objects = RelatedModel._meta.get_all_related_objects_with_model(
            include_hidden=True)
        self.eq_field_names_and_models(objects, [
            'model_options:firstrelatingobject',
            'model_options:secondrelatinghiddenobject',
            'model_options:firstrelatinghiddenobject',
            'model_options:secondrelatingobject'
        ], [BaseRelatedModel, None, BaseRelatedModel, None])

    def test_related_objects_include_hidden_local_only(self):
        objects = RelatedModel._meta.get_all_related_objects_with_model(
            include_hidden=True, local_only=True)
        self.eq_field_names_and_models(objects, [
            'model_options:secondrelatingobject',
            'model_options:secondrelatinghiddenobject'
        ], [None, None])

    def test_related_objects_proxy(self):
        objects = RelatedModel._meta.get_all_related_objects_with_model(
            include_proxy_eq=True)
        self.eq_field_names_and_models(objects, [
            'model_options:firstrelatingobject',
            'model_options:relatingobjecttoproxy',
            'model_options:secondrelatingobject'
        ], [BaseRelatedModel, None, None])

    def test_related_objects_proxy_hidden(self):
        objects = RelatedModel._meta.get_all_related_objects_with_model(
            include_proxy_eq=True, include_hidden=True)
        self.eq_field_names_and_models(objects, [
            'model_options:relatinghiddenobjecttoproxy',
            'model_options:secondrelatingobject',
            'model_options:firstrelatingobject',
            'model_options:firstrelatinghiddenobject',
            'model_options:secondrelatinghiddenobject',
            'model_options:relatingobjecttoproxy'
        ], [None, None, BaseRelatedModel, BaseRelatedModel,
            None, None])


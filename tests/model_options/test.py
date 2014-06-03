from django import test

from django.db.models import CharField, ManyToManyField
from django.db.models.fields.related import (
    ManyToManyRel, RelatedObject, OneToOneField
)

from django.contrib.auth.models import User

from .models import (
    Musician, Group,
    Data, SuperData, M2MModel,
    SuperM2MModel,
    RelatedModel, BaseRelatedModel,
    RelatedM2MModel, BaseRelatedM2MModel,
    BareModel,
    A, B, C
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

    def test_related_m2m_with_model(self):
        objects = RelatedM2MModel._meta.get_all_related_m2m_objects_with_model()
        self.eq_field_names_and_models(objects, [
            'model_options:m2mrelationtobasem2mmodel',
            'model_options:m2mrelationtom2mmodel'
        ], [BaseRelatedM2MModel, None])

    def test_related_m2m_local_only(self):
        fields = RelatedM2MModel._meta.get_all_related_many_to_many_objects(
            local_only=True)
        self.assertEquals([f.name for f in fields], [
            'model_options:m2mrelationtom2mmodel'
        ])

    def test_add_data_field(self):
        cf = CharField()
        cf.set_attributes_from_name("my_new_field")
        BareModel._meta.add_field(cf)

        self.assertEquals([u'id', 'my_new_field'], [f.attname
                          for f in BareModel._meta.fields])

    def test_add_m2m_field(self):
        cf = ManyToManyField(User)
        cf.set_attributes_from_name("my_new_field")
        BareModel._meta.add_field(cf)

        self.assertEquals(['my_new_field'], [f.attname for f in
                          BareModel._meta.many_to_many])

    def test_get_data_field(self):
        field_info = Musician._meta.get_field_by_name('name')
        self.assertEquals(field_info[1:], (None, True, False))
        self.assertTrue(isinstance(field_info[0], CharField))

    def test_get_m2m_field(self):
        field_info = Group._meta.get_field_by_name('members')
        self.assertEquals(field_info[1:], (None, True, True))
        self.assertTrue(isinstance(field_info[0], ManyToManyField))

    def test_get_related_object(self):
        field_info = Group._meta.get_field_by_name('ownedvenue')
        self.assertEquals(field_info[1:], (None, False, False))
        self.assertTrue(isinstance(field_info[0], RelatedObject))

    def test_get_related_m2m(self):
        field_info = Musician._meta.get_field_by_name('group')
        self.assertEquals(field_info[1:], (None, False, True))
        self.assertTrue(isinstance(field_info[0], RelatedObject))

    def test_get_parent_field(self):
        field_info = SuperData._meta.get_field_by_name('name_data')
        self.assertEquals(field_info[1:], (Data, True, False))
        self.assertTrue(isinstance(field_info[0], CharField))

    def test_get_ancestor_link(self):
        field = SuperData._meta.get_ancestor_link(Data)
        self.assertTrue(isinstance(field, OneToOneField))
        self.assertEquals(field.related_query_name(), 'superdata')

    def test_get_ancestor_link_multiple(self):
        info = C._meta.get_ancestor_link(A)
        self.assertEquals('b_ptr_id', info.attname)

    def test_get_ancestor_link_invalid(self):
        self.assertFalse(SuperData._meta.get_ancestor_link(Musician))

    def test_get_base_chain(self):
        chain = C._meta.get_base_chain(A)
        self.assertEquals(chain, [B, A])

    def test_get_base_chain_invalid(self):
        self.assertFalse(C._meta.get_base_chain(Musician))

    def test_get_parent_list(self):
        self.assertEquals(C._meta.get_parent_list(), set([
                          B, A]))

from django import test

from django.db.models import CharField, ManyToManyField
from django.db.models.options import (
    DATA, M2M, RELATED_OBJECTS, RELATED_M2M,
    LOCAL_ONLY, CONCRETE, INCLUDE_PROXY, INCLUDE_HIDDEN, NONE
)
from django.db.models.fields.related import (
    ManyToManyRel, RelatedObject, OneToOneField
)

from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation
)
from django.contrib.auth.models import User

from .models import (
    Musician, Group,
    Data, SuperData, M2MModel,
    SuperM2MModel,
    RelatedModel, BaseRelatedModel,
    RelatedM2MModel, BaseRelatedM2MModel,
    BareModel,
    A, B, C,
    ModelWithGenericFK, AGenericRelation
)

from collections import OrderedDict


class OptionsBaseTests(test.TestCase):
    def assertContainsOfType(self, model, objects, names_and_models, opts=NONE):
        self.assertEquals(len(objects), len(names_and_models))

        field_names = dict([(f.name, n) for n, f in objects])
        gfd = model._meta.get_field_details
        for expected_name, expected_model in names_and_models:
            self.assertTrue(expected_name in field_names.keys())
            self.assertEquals(gfd(field_names[expected_name], opts=opts)[1],
                              expected_model)

    def eq_field_names_and_models(self, objects, names_eq, models_eq):
        fields, models = zip(*objects)
        self.assertEquals(set([f.name for f in fields]), set(names_eq))
        self.assertEquals(set(models), set(models_eq))


class NewAPITests(OptionsBaseTests):

    def test_local_fields(self):
        fields = SuperData._meta.get_new_fields(types=DATA,
                                                opts=LOCAL_ONLY)
        self.assertEquals(set([n for n, f in fields]), set([
            'data_ptr_id',
            'name_super_data',
            'surname_super_data',
            'origin_super_data'
        ]))
        self.assertTrue(all([f.rel is None or not isinstance(f.rel, ManyToManyRel)
                             for n, f in fields]))

    def test_local_concrete_fields(self):
        fields = SuperData._meta.get_new_fields(types=DATA,
                                                opts=LOCAL_ONLY | CONCRETE)
        self.assertEquals([n for n, f in fields], [
            u'data_ptr_id',
            'name_super_data',
            'surname_super_data'
        ])
        self.assertTrue(all([f.column is not None
                             for n, f in fields]))

    def test_many_to_many(self):
        fields = SuperM2MModel._meta.get_new_fields(types=M2M)
        self.assertEquals([f.attname for n, f in fields], [
            'members',
            'members_super'
        ])
        self.assertTrue(all([isinstance(f.rel, ManyToManyRel)
                             for n, f in fields]))

    def test_many_to_many_with_model(self):
        fields = SuperM2MModel._meta.get_new_fields(types=M2M)
        models = [SuperM2MModel._meta.get_field_details(n)[1]
                  for n, f in fields]
        self.assertEquals(len(models), 2)
        self.assertEquals(models[0], M2MModel)
        self.assertEquals(models[1], SuperM2MModel)

    def test_related_objects(self):
        objects = RelatedModel._meta.get_new_fields(types=RELATED_OBJECTS)
        self.assertContainsOfType(RelatedModel, objects, (
            ('model_options:firstrelatingobject', BaseRelatedModel),
            ('model_options:secondrelatingobject', RelatedModel),
        ))

    def test_related_objects_local(self):
        objects = RelatedModel._meta.get_new_fields(types=RELATED_OBJECTS,
                                                    opts=LOCAL_ONLY)
        self.assertContainsOfType(RelatedModel, objects, (
            ('model_options:secondrelatingobject', RelatedModel),
        ))

    def test_related_objects_include_hidden(self):
        objects = RelatedModel._meta.get_new_fields(types=RELATED_OBJECTS,
                                                    opts=INCLUDE_HIDDEN)
        self.assertContainsOfType(RelatedModel, objects, (
            ('model_options:secondrelatingobject', RelatedModel),
            ('model_options:secondrelatinghiddenobject', RelatedModel),
            ('model_options:firstrelatingobject', BaseRelatedModel),
            ('model_options:firstrelatinghiddenobject', BaseRelatedModel),
        ), opts=INCLUDE_HIDDEN)

    def test_related_objects_include_hidden_local_only(self):
        objects = RelatedModel._meta.get_new_fields(types=RELATED_OBJECTS,
                                                    opts=INCLUDE_HIDDEN | LOCAL_ONLY)
        self.assertContainsOfType(RelatedModel, objects, (
            ('model_options:secondrelatingobject', RelatedModel),
            ('model_options:secondrelatinghiddenobject', RelatedModel),
        ), opts=INCLUDE_HIDDEN | LOCAL_ONLY)

    def test_related_objects_proxy(self):
        objects = RelatedModel._meta.get_new_fields(types=RELATED_OBJECTS,
                                                    opts=INCLUDE_HIDDEN | INCLUDE_PROXY)
        self.assertContainsOfType(RelatedModel, objects, (
            ('model_options:secondrelatingobject', RelatedModel),
            ('model_options:secondrelatinghiddenobject', RelatedModel),
            ('model_options:firstrelatingobject', BaseRelatedModel),
            ('model_options:firstrelatinghiddenobject', BaseRelatedModel),
            ('model_options:relatingobjecttoproxy', RelatedModel),
            ('model_options:relatinghiddenobjecttoproxy', RelatedModel)
        ), opts=INCLUDE_HIDDEN | INCLUDE_PROXY)

    def test_related_m2m_with_model(self):
        objects = RelatedM2MModel._meta.get_new_fields(types=RELATED_M2M)
        self.assertContainsOfType(RelatedM2MModel, objects, (
            ('model_options:m2mrelationtobasem2mmodel', BaseRelatedM2MModel),
            ('model_options:m2mrelationtom2mmodel', RelatedM2MModel)
        ))

    def test_related_m2m_local_only(self):
        objects = RelatedM2MModel._meta.get_new_fields(types=RELATED_M2M,
                                                       opts=LOCAL_ONLY)
        self.assertContainsOfType(RelatedM2MModel, objects, (
            ('model_options:m2mrelationtom2mmodel', RelatedM2MModel),
        ), opts=LOCAL_ONLY)


class LegacyAPITests(OptionsBaseTests):

    def test_local_fields(self):
        fields = SuperData._meta.local_fields
        self.assertEquals(set([f.attname for f in fields]), set([
            'data_ptr_id',
            'name_super_data',
            'surname_super_data',
            'origin_super_data'
        ]))
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
        models = [m for n, m in SuperM2MModel._meta.get_m2m_with_model()]
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

    def test_virtual_field(self):
        virtual_fields = ModelWithGenericFK._meta.virtual_fields
        self.assertEquals(len(virtual_fields), 1)
        self.assertTrue(isinstance(virtual_fields[0],
                        GenericForeignKey))

    def test_virtual_field_generic_relation(self):
        virtual_fields = AGenericRelation._meta.virtual_fields
        self.assertEquals(len(virtual_fields), 1)
        self.assertTrue(isinstance(virtual_fields[0],
                        GenericRelation))

        objects = ModelWithGenericFK._meta.get_all_related_objects(
            include_hidden=True)
        self.assertEquals([f.name for f in objects],
                          ["model_options:agenericrelation"])


class ComparisonBaseTests(test.TestCase):

    def get_fields(self, Model, **kwargs):
        return Model._meta.get_new_fields(**kwargs)

    def map_model(self, new_fields):
        return [f for n, f in new_fields]

    def assertEqualFields(self, old_fields, new_fields):
        uniq_old_fields = [x for x, y in old_fields]
        uniq_new_fields = [y for x, y in new_fields]
        self.assertEquals(uniq_new_fields, uniq_old_fields)


class ComparisonDataTests(ComparisonBaseTests):

    def test_data_local(self):
        new_fields = self.get_fields(SuperData, types=DATA, opts=LOCAL_ONLY)
        old_fields = SuperData._meta.local_fields
        self.assertEqual(old_fields, self.map_model(new_fields))

    def test_data(self):
        new_fields = self.get_fields(SuperData, types=DATA)
        old_fields = SuperData._meta.get_fields_with_model()
        self.assertEqualFields(old_fields, new_fields)

    def test_data_local_concrete(self):
        new_fields = self.get_fields(SuperData, types=DATA,
                                     opts=LOCAL_ONLY | CONCRETE)
        old_fields = SuperData._meta.local_concrete_fields
        self.assertEqual(old_fields, self.map_model(new_fields))

    def test_data_concrete(self):
        new_fields = self.get_fields(SuperData, types=DATA, opts=CONCRETE)
        old_fields = SuperData._meta.concrete_fields
        self.assertEqual(old_fields, self.map_model(new_fields))


class ComparisonM2MTests(ComparisonBaseTests):

    def test_m2m(self):
        new_fields = self.get_fields(SuperM2MModel, types=M2M)
        old_fields = SuperM2MModel._meta.get_m2m_with_model()
        self.assertEqualFields(old_fields, new_fields)

    def test_m2m_local(self):
        new_fields = self.get_fields(SuperM2MModel, types=M2M,
                                     opts=LOCAL_ONLY)
        old_fields = SuperM2MModel._meta.local_many_to_many
        self.assertEqual(old_fields, self.map_model(new_fields))


class ComparisonRelatedObjectsTest(ComparisonBaseTests):

    def test_related_objects(self):
        new_fields = self.get_fields(RelatedModel,
                                     types=RELATED_OBJECTS)
        old_fields = RelatedModel._meta.get_all_related_objects_with_model()
        self.assertEqualFields(old_fields, new_fields)

    def test_related_objects_local(self):
        new_fields = self.get_fields(RelatedModel,
                                     types=RELATED_OBJECTS,
                                     opts=LOCAL_ONLY)
        old_fields = RelatedModel._meta.get_all_related_objects_with_model(
            local_only=True)
        self.assertEqualFields(old_fields, new_fields)

    def test_related_objects_include_hidden(self):
        new_fields = self.get_fields(RelatedModel,
                                     types=RELATED_OBJECTS,
                                     opts=INCLUDE_HIDDEN)
        old_fields = RelatedModel._meta.get_all_related_objects_with_model(
            include_hidden=True)
        self.assertEqualFields(old_fields, new_fields)

    def test_related_objects_include_hidden_local_only(self):
        new_fields = self.get_fields(RelatedModel,
                                     types=RELATED_OBJECTS,
                                     opts=INCLUDE_HIDDEN | LOCAL_ONLY)
        old_fields = RelatedModel._meta.get_all_related_objects_with_model(
            include_hidden=True, local_only=True)
        self.assertEqualFields(old_fields, new_fields)

    def test_related_objects_proxy(self):
        new_fields = self.get_fields(RelatedModel,
                                     types=RELATED_OBJECTS,
                                     opts=INCLUDE_PROXY)
        old_fields = RelatedModel._meta.get_all_related_objects_with_model(
            include_proxy_eq=True)
        self.assertEqualFields(old_fields, new_fields)

    def test_related_objects_proxy_hidden(self):
        new_fields = self.get_fields(RelatedModel,
                                     types=RELATED_OBJECTS,
                                     opts=INCLUDE_PROXY | INCLUDE_HIDDEN)
        old_fields = RelatedModel._meta.get_all_related_objects_with_model(
            include_proxy_eq=True, include_hidden=True)
        self.assertTrue(OrderedDict(new_fields)['object_to_proxy_hidden_id'])
        self.assertEqualFields(old_fields, new_fields)


class ComparisonRelatedM2MTest(ComparisonBaseTests):

    def test_related_m2m_objects(self):
        old_fields = Musician._meta.get_all_related_many_to_many_objects()
        new_fields = Musician._meta.get_new_fields(types=RELATED_M2M)
        uniq_new_fields = [y for x, y in new_fields]
        self.assertEquals(uniq_new_fields, old_fields)

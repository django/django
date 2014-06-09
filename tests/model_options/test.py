from django import test

from django.db.models import CharField, ManyToManyField
from django.db.models.fields.related import (
    ManyToManyRel, RelatedObject, OneToOneField
)

from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation
)
from django.contrib.auth.models import User

from .models import (
    AbstractData, BaseData, Data, ConcreteData,

    AbstractM2M, BaseM2M, M2M,

    BaseRelatedObject, RelatedObject,
    ProxyRelatedObject, HiddenRelatedObject
)

from collections import OrderedDict


class OptionsBaseTests(test.TestCase):
    def eq_field_names_and_models(self, objects, names_eq, models_eq):
        fields, models = zip(*objects)
        self.assertEquals([f.name for f in fields], names_eq)
        self.assertEquals(models, models_eq)


class DataTests(OptionsBaseTests):

    def test_fields(self):
        fields = Data._meta.fields
        self.assertEquals([f.attname for f in fields], [
                          u'id', 'name_abstract', 'name_base',
                          u'basedata_ptr_id', 'name'])

    def test_local_fields(self):
        fields = Data._meta.local_fields
        self.assertEquals([f.attname for f in fields], [
                          u'basedata_ptr_id', 'name'])
        self.assertTrue(all([f.rel is None or not isinstance(f.rel, ManyToManyRel)
                             for f in fields]))

    def test_local_concrete_fields(self):
        fields = ConcreteData._meta.local_concrete_fields
        self.assertEquals([f.attname for f in fields], [
                          u'data_ptr_id', 'name_concrete'])
        self.assertTrue(all([f.column is not None
                             for f in fields]))


class M2MTests(OptionsBaseTests):

    def test_many_to_many(self):
        fields = M2M._meta.many_to_many
        self.assertEquals([f.attname for f in fields], [
                          'm2m_abstract', 'm2m_base', 'm2m'])
        self.assertTrue(all([isinstance(f.rel, ManyToManyRel)
                             for f in fields]))

    def test_many_to_many_with_model(self):
        models = OrderedDict(M2M._meta.get_m2m_with_model()).values()
        self.assertEquals(models, [AbstractM2M, BaseM2M, None])


class RelatedObjectsTests(OptionsBaseTests):

    def test_related_objects(self):
        objects = RelatedObject._meta.get_all_related_objects_with_model()
        self.eq_field_names_and_models(objects, [
            'model_options:relbaserelatedobjects',
            'model_options:relrelatedobjects',
            u'model_options:hiddenrelatedobject'
        ], (BaseRelatedObject, None, None))

    def test_related_objects_local(self):
        objects = RelatedObject._meta.get_all_related_objects_with_model(
            local_only=True)
        self.eq_field_names_and_models(objects, [
            'model_options:relrelatedobjects',
            'model_options:hiddenrelatedobject'
        ], (None, None))

    def test_related_objects_include_hidden(self):
        objects = HiddenRelatedObject._meta.get_all_related_objects_with_model(
            include_hidden=True)
        self.eq_field_names_and_models(objects, [
            'model_options:relbaserelatedobjects',
            'model_options:relrelatedobjects',
            'model_options:relhiddenrelatedobjects'
        ], (BaseRelatedObject, RelatedObject, None))

    def test_related_objects_include_hidden_local_only(self):
        objects = HiddenRelatedObject._meta.get_all_related_objects_with_model(
            include_hidden=True, local_only=True)
        self.eq_field_names_and_models(objects, [
            'model_options:relhiddenrelatedobjects'
        ], (None,))

    def test_related_objects_proxy(self):
        objects = RelatedObject._meta.get_all_related_objects_with_model(
            include_proxy_eq=True)
        self.eq_field_names_and_models(objects, [
            'model_options:relbaserelatedobjects',
            'model_options:relrelatedobjects',
            'model_options:relproxyrelatedobjects',
            'model_options:hiddenrelatedobject',
        ], (BaseRelatedObject, None, None, None))

    def test_related_objects_proxy_hidden(self):
        objects = RelatedObject._meta.get_all_related_objects_with_model(
            include_proxy_eq=True, include_hidden=True)
        self.eq_field_names_and_models(objects, [
            'model_options:relbaserelatedobjects',
            'model_options:relrelatedobjects',
            'model_options:relproxyrelatedobjects',
            'model_options:relproxyhiddenrelatedobjects',
            'model_options:hiddenrelatedobject',
        ], (BaseRelatedObject, None, None, None, None))

    #def test_related_m2m_with_model(self):
        #objects = RelatedM2MModel._meta.get_all_related_m2m_objects_with_model()
        #self.eq_field_names_and_models(objects, [
            #'model_options:m2mrelationtobasem2mmodel',
            #'model_options:m2mrelationtom2mmodel'
        #], [BaseRelatedM2MModel, None])

    #def test_related_m2m_local_only(self):
        #fields = RelatedM2MModel._meta.get_all_related_many_to_many_objects(
            #local_only=True)
        #self.assertEquals([f.name for f in fields], [
            #'model_options:m2mrelationtom2mmodel'
        #])

    #def test_add_data_field(self):
        #cf = CharField()
        #cf.set_attributes_from_name("my_new_field")
        #BareModel._meta.add_field(cf)

        #self.assertEquals([u'id', 'my_new_field'], [f.attname
                          #for f in BareModel._meta.fields])

    #def test_add_m2m_field(self):
        #cf = ManyToManyField(User)
        #cf.set_attributes_from_name("my_new_field")
        #BareModel._meta.add_field(cf)

        #self.assertEquals(['my_new_field'], [f.attname for f in
                          #BareModel._meta.many_to_many])

    #def test_get_data_field(self):
        #field_info = Musician._meta.get_field_by_name('name')
        #self.assertEquals(field_info[1:], (None, True, False))
        #self.assertTrue(isinstance(field_info[0], CharField))

    #def test_get_m2m_field(self):
        #field_info = Group._meta.get_field_by_name('members')
        #self.assertEquals(field_info[1:], (None, True, True))
        #self.assertTrue(isinstance(field_info[0], ManyToManyField))

    #def test_get_related_object(self):
        #field_info = Group._meta.get_field_by_name('ownedvenue')
        #self.assertEquals(field_info[1:], (None, False, False))
        #self.assertTrue(isinstance(field_info[0], RelatedObject))

    #def test_get_related_m2m(self):
        #field_info = Musician._meta.get_field_by_name('group')
        #self.assertEquals(field_info[1:], (None, False, True))
        #self.assertTrue(isinstance(field_info[0], RelatedObject))

    #def test_get_parent_field(self):
        #field_info = SuperData._meta.get_field_by_name('name_data')
        #self.assertEquals(field_info[1:], (Data, True, False))
        #self.assertTrue(isinstance(field_info[0], CharField))

    #def test_get_ancestor_link(self):
        #field = SuperData._meta.get_ancestor_link(Data)
        #self.assertTrue(isinstance(field, OneToOneField))
        #self.assertEquals(field.related_query_name(), 'superdata')

    #def test_get_ancestor_link_multiple(self):
        #info = C._meta.get_ancestor_link(A)
        #self.assertEquals('b_ptr_id', info.attname)

    #def test_get_ancestor_link_invalid(self):
        #self.assertFalse(SuperData._meta.get_ancestor_link(Musician))

    #def test_get_base_chain(self):
        #chain = C._meta.get_base_chain(A)
        #self.assertEquals(chain, [B, A])

    #def test_get_base_chain_invalid(self):
        #self.assertFalse(C._meta.get_base_chain(Musician))

    #def test_get_parent_list(self):
        #self.assertEquals(C._meta.get_parent_list(), set([
                          #B, A]))

    #def test_virtual_field(self):
        #virtual_fields = ModelWithGenericFK._meta.virtual_fields
        #self.assertEquals(len(virtual_fields), 1)
        #self.assertTrue(isinstance(virtual_fields[0],
                        #GenericForeignKey))

    #def test_virtual_field_generic_relation(self):
        #virtual_fields = AGenericRelation._meta.virtual_fields
        #self.assertEquals(len(virtual_fields), 1)
        #self.assertTrue(isinstance(virtual_fields[0],
                        #GenericRelation))

        #objects = ModelWithGenericFK._meta.get_all_related_objects(
            #include_hidden=True)
        #self.assertEquals([f.name for f in objects],
                          #["model_options:agenericrelation"])

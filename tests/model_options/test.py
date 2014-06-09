from django import test
from collections import OrderedDict

from django.db.models import fields
from django.db.models.fields.related import (
    ManyToManyRel, ManyToManyField
)

from .models import (
    BaseData, Data, ConcreteData,
    BaseM2M, M2M,
    BaseRelatedObject, RelatedObject, HiddenRelatedObject,
    BaseRelatedM2M, RelatedM2M
)


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
        self.assertEquals(models, [BaseM2M, BaseM2M, None])


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


class RelatedM2MTests(OptionsBaseTests):

    def test_related_m2m_with_model(self):
        objects = RelatedM2M._meta.get_all_related_m2m_objects_with_model()
        self.eq_field_names_and_models(objects, [
            'model_options:relbaserelatedm2m',
            'model_options:relrelatedm2m'
        ], (BaseRelatedM2M, None))

    def test_related_m2m_local_only(self):
        objects = RelatedM2M._meta.get_all_related_many_to_many_objects(
            local_only=True)
        self.assertEquals([o.name for o in objects], [
            'model_options:relrelatedm2m'
        ])

    def test_get_data_field(self):
        field_info = Data._meta.get_field_by_name('name_abstract')
        self.assertEquals(field_info[1:], (BaseData, True, False))
        self.assertTrue(isinstance(field_info[0], fields.CharField))

    def test_get_m2m_field(self):
        field_info = M2M._meta.get_field_by_name('m2m_base')
        self.assertEquals(field_info[1:], (BaseM2M, True, True))
        self.assertTrue(isinstance(field_info[0], ManyToManyField))

    def test_get_related_object(self):
        field_info = RelatedObject._meta.get_field_by_name('relrelatedobjects')
        self.assertEquals(field_info[1:], (None, False, False))
        #self.assertTrue(isinstance(field_info[0], RelatedObject))

    def test_get_related_m2m(self):
        field_info = RelatedM2M._meta.get_field_by_name('relrelatedm2m')
        self.assertEquals(field_info[1:], (None, False, True))
        #self.assertTrue(isinstance(field_info[0], RelatedObject))

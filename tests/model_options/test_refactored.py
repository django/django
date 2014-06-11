from django import test
from collections import OrderedDict

from django.db.models.fields import related, CharField
from django.contrib.contenttypes.fields import GenericForeignKey

from django.db.models.options import (
    DATA, M2M as _M2M, RELATED_OBJECTS, RELATED_M2M, VIRTUAL,
    LOCAL_ONLY, CONCRETE, INCLUDE_PROXY, INCLUDE_HIDDEN, NONE
)

from .models import (
    BaseData, Data, ConcreteData,
    BaseM2M, M2M,
    BaseRelatedObject, RelatedObject, HiddenRelatedObject,
    BaseRelatedM2M, RelatedM2M,
    RelatedM2MRecursiveSymmetrical, RelatedM2MRecursiveAsymmetrical,
    Virtual
)


class OptionsBaseTests(test.TestCase):
    def eq_field_names_and_models(self, objects, names_eq, models_eq):
        fields, models = zip(*objects)
        self.assertEquals([f.name for f in fields], names_eq)
        self.assertEquals(models, models_eq)

    def fields(self, res):
        return [f for fn, f in res]

    def fields_models(self, m, res, opts=NONE):
        models = [m._meta.get_field_details(fn, opts=opts)[1] for fn, f in res]
        fields = [f for fn, f in res]
        return zip(fields, map(lambda model: None if m == model else model, models))

    def _map_none(self, m, res):
        res = list(res)
        if res[1] == m:
            res[1] = None
        return tuple(res)


class DataTests(OptionsBaseTests):

    def test_fields(self):
        fields = self.fields(Data._meta.get_new_fields(types=DATA))
        self.assertEquals([f.attname for f in fields], [
                          u'id', 'name_abstract', 'name_base',
                          u'basedata_ptr_id', 'name'])

    def test_local_fields(self):
        fields = self.fields(Data._meta.get_new_fields(types=DATA, opts=LOCAL_ONLY))
        self.assertEquals([f.attname for f in fields], [
                          u'basedata_ptr_id', 'name'])
        self.assertTrue(all([f.rel is None or not isinstance(f.rel,
                        related.ManyToManyRel) for f in fields]))

    def test_local_concrete_fields(self):
        fields = self.fields(ConcreteData._meta.get_new_fields(types=DATA,
                                                       opts=LOCAL_ONLY | CONCRETE))
        self.assertEquals([f.attname for f in fields], [
                          u'data_ptr_id', 'name_concrete'])
        self.assertTrue(all([f.column is not None
                             for f in fields]))


class M2MTests(OptionsBaseTests):

    def test_many_to_many(self):
        fields = self.fields(M2M._meta.get_new_fields(types=_M2M))
        self.assertEquals([f.attname for f in fields], [
                          'm2m_abstract', 'm2m_base', 'm2m'])
        self.assertTrue(all([isinstance(f.rel, related.ManyToManyRel)
                             for f in fields]))

    def test_many_to_many_with_model(self):
        objects = self.fields_models(M2M, M2M._meta.get_new_fields(types=_M2M))
        self.assertEquals([m for f, m in objects], [BaseM2M, BaseM2M, None])


class RelatedObjectsTests(OptionsBaseTests):

    def test_related_objects(self):
        objects = self.fields_models(RelatedObject, RelatedObject._meta.get_new_fields(
                                     types=RELATED_OBJECTS))
        self.eq_field_names_and_models(objects, [
            'model_options:relbaserelatedobjects',
            'model_options:relrelatedobjects',
            u'model_options:hiddenrelatedobject'
        ], (BaseRelatedObject, None, None))

    def test_related_objects_local(self):
        objects = self.fields_models(RelatedObject, RelatedObject._meta.get_new_fields(
                                     types=RELATED_OBJECTS, opts=LOCAL_ONLY), LOCAL_ONLY)
        self.eq_field_names_and_models(objects, [
            'model_options:relrelatedobjects',
            'model_options:hiddenrelatedobject'
        ], (None, None))

    def test_related_objects_include_hidden(self):
        objects = self.fields_models(HiddenRelatedObject, HiddenRelatedObject._meta.get_new_fields(
                                     types=RELATED_OBJECTS, opts=INCLUDE_HIDDEN), INCLUDE_HIDDEN)
        self.eq_field_names_and_models(objects, [
            'model_options:relbaserelatedobjects',
            'model_options:relrelatedobjects',
            'model_options:relhiddenrelatedobjects'
        ], (BaseRelatedObject, RelatedObject, None))

    def test_related_objects_include_hidden_local_only(self):
        opts = INCLUDE_HIDDEN | LOCAL_ONLY
        objects = self.fields_models(HiddenRelatedObject, HiddenRelatedObject._meta.get_new_fields(
                                     types=RELATED_OBJECTS, opts=opts), opts)
        self.eq_field_names_and_models(objects, [
            'model_options:relhiddenrelatedobjects'
        ], (None,))

    def test_related_objects_proxy(self):
        objects = self.fields_models(RelatedObject, RelatedObject._meta.get_new_fields(
                                     types=RELATED_OBJECTS, opts=INCLUDE_PROXY), INCLUDE_PROXY)
        self.eq_field_names_and_models(objects, [
            'model_options:relbaserelatedobjects',
            'model_options:relrelatedobjects',
            'model_options:relproxyrelatedobjects',
            'model_options:hiddenrelatedobject',
        ], (BaseRelatedObject, None, None, None))

    def test_related_objects_proxy_hidden(self):
        opts = INCLUDE_HIDDEN | INCLUDE_PROXY
        objects = self.fields_models(RelatedObject, RelatedObject._meta.get_new_fields(
                                     types=RELATED_OBJECTS, opts=opts), opts)
        self.eq_field_names_and_models(objects, [
            'model_options:relbaserelatedobjects',
            'model_options:relrelatedobjects',
            'model_options:relproxyrelatedobjects',
            'model_options:relproxyhiddenrelatedobjects',
            'model_options:hiddenrelatedobject',
        ], (BaseRelatedObject, None, None, None, None))


class RelatedM2MTests(OptionsBaseTests):

    def test_related_m2m_with_model(self):
        objects = self.fields_models(RelatedM2M, RelatedM2M._meta.get_new_fields(
                                     types=RELATED_M2M))
        self.eq_field_names_and_models(objects, [
            'model_options:relbaserelatedm2m',
            'model_options:relrelatedm2m'
        ], (BaseRelatedM2M, None))

    def test_related_m2m_local_only(self):
        opts = LOCAL_ONLY
        objects = [f for fn, f in RelatedM2M._meta.get_new_fields(
                   types=RELATED_M2M, opts=opts)]
        self.assertEquals([o.name for o in objects], [
            'model_options:relrelatedm2m'
        ])

    def test_related_m2m_asymmetrical(self):
        m2m = RelatedM2MRecursiveAsymmetrical._meta.get_new_fields(types=_M2M)
        self.assertEquals([fn for fn, f in m2m],
                          ['following'])
        related_m2m = RelatedM2MRecursiveAsymmetrical._meta.get_new_fields(
            types=RELATED_M2M)
        self.assertEquals([fn for fn, f in related_m2m],
                          ['followers'])

    def test_related_m2m_symmetrical(self):
        m2m = RelatedM2MRecursiveSymmetrical._meta.get_new_fields(types=_M2M)
        self.assertEquals([fn for fn, f in m2m],
                          ['friends'])
        related_m2m = RelatedM2MRecursiveSymmetrical._meta.get_new_fields(
            types=RELATED_M2M)
        self.assertEquals([fn for fn, f in related_m2m],
                          ['friends_rel_+'])


class VirtualFieldsTests(OptionsBaseTests):

    def test_virtual_fields(self):
        self.assertEquals([fn for fn, f in Virtual._meta.get_new_fields(types=VIRTUAL)], [
                          'content_object'])


class GetFieldByNameTests(OptionsBaseTests):

    def test_get_data_field(self):
        field_info = self._map_none(Data, Data._meta.get_field_details('name_abstract'))
        self.assertEquals(field_info[1:], (BaseData, True, False))
        self.assertTrue(isinstance(field_info[0], CharField))

    def test_get_m2m_field(self):
        field_info = self._map_none(M2M, M2M._meta.get_field_details('m2m_base'))
        self.assertEquals(field_info[1:], (BaseM2M, True, True))
        self.assertTrue(isinstance(field_info[0], related.ManyToManyField))

    def test_get_related_object(self):
        field_info = self._map_none(RelatedObject, RelatedObject._meta.get_field_details('relrelatedobjects'))
        self.assertEquals(field_info[1:], (None, False, False))
        self.assertTrue(isinstance(field_info[0], related.RelatedObject))

    def test_get_related_m2m(self):
        field_info = self._map_none(RelatedM2M, RelatedM2M._meta.get_field_details('relrelatedm2m'))
        self.assertEquals(field_info[1:], (None, False, True))
        self.assertTrue(isinstance(field_info[0], related.RelatedObject))

    def test_get_virtual_field(self):
        field_info = self._map_none(Virtual, Virtual._meta.get_field_details('content_object'))
        self.assertEquals(field_info[1:], (None, True, False))
        self.assertTrue(isinstance(field_info[0], GenericForeignKey))

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType


# DATA
class RelatedConcreteData(models.Model):
    pass


class AbstractData(models.Model):
    class Meta:
        abstract = True
    name_abstract = models.CharField(max_length=10)


class BaseData(AbstractData):
    name_base = models.CharField(max_length=10)


class Data(BaseData):
    name = models.CharField(max_length=10)


class ConcreteData(Data):
    name_concrete = models.CharField(max_length=10)
    non_concrete_relationship = models.ForeignObject(RelatedConcreteData,
            from_fields=['non_concrete_id'], to_fields=['id'])


# M2M

# RELATIONS
class RelatedAbstractM2M(models.Model):
    pass


class RelatedBaseM2M(models.Model):
    pass


class RelatedM2M(models.Model):
    pass


# MODELS
class AbstractM2M(models.Model):
    m2m_abstract = models.ManyToManyField(RelatedAbstractM2M)


class BaseM2M(AbstractM2M):
    m2m_base = models.ManyToManyField(RelatedBaseM2M)


class M2M(BaseM2M):
    m2m = models.ManyToManyField(RelatedM2M)


# RELATED_OBJECTS
class BaseRelatedModel(models.Model):
    name_base = models.CharField(max_length=10)


class FirstRelatingObject(models.Model):
    model_base_first = models.ForeignKey(BaseRelatedModel)


class FirstRelatingHiddenObject(models.Model):
    model_hidden_base_first = models.ForeignKey(BaseRelatedModel,
                                                related_name='+')


class RelatedModel(BaseRelatedModel):
    name = models.CharField(max_length=10)


class SecondRelatingObject(models.Model):
    model_base_second = models.ForeignKey(RelatedModel)


class SecondRelatingHiddenObject(models.Model):
    model_hidden_base_second = models.ForeignKey(RelatedModel,
                                                 related_name='+')


class RelatedModelProxy(RelatedModel):
    class Meta:
        proxy = True


class RelatingObjectToProxy(models.Model):
    object_to_proxy = models.ForeignKey(RelatedModelProxy)


class RelatingHiddenObjectToProxy(models.Model):
    object_to_proxy_hidden = models.ForeignKey(RelatedModelProxy,
                                               related_name='+')


# RELATED_M2M
class BaseRelatedM2MModel(models.Model):
    name_base = models.CharField(max_length=10)


class M2MRelationToBaseM2MModel(models.Model):
    relation_base = models.ManyToManyField(BaseRelatedM2MModel)


class RelatedM2MModel(BaseRelatedM2MModel):
    name = models.CharField(max_length=10)


class M2MRelationToM2MModel(models.Model):
    relation = models.ManyToManyField(RelatedM2MModel)


class BareModel(models.Model):
    pass


# CHAIN
class A(models.Model):
    pass


class B(A):
    pass


class C(B):
    pass


# VIRTUAL FIELDS
class ModelWithGenericFK(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')


class AGenericRelation(models.Model):
    generic_model = GenericRelation(ModelWithGenericFK)

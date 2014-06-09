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
# M2M RELATIONS
class RelAbstractM2M(models.Model):
    pass


class RelBaseM2M(models.Model):
    pass


class RelM2M(models.Model):
    pass


# M2M MODELS
class AbstractM2M(models.Model):
    m2m_abstract = models.ManyToManyField(RelAbstractM2M)

    class Meta:
        abstract = True


class BaseM2M(AbstractM2M):
    m2m_base = models.ManyToManyField(RelBaseM2M)


class M2M(BaseM2M):
    m2m = models.ManyToManyField(RelM2M)


# RELATED_OBJECTS
# RELATED_OBJECTS RELATIONS
class RelBaseRelatedObjects(models.Model):
    rel_base = models.ForeignKey('BaseRelatedObject')


class RelRelatedObjects(models.Model):
    rel = models.ForeignKey('RelatedObject')


class RelHiddenRelatedObjects(models.Model):
    rel_hidden = models.ForeignKey('HiddenRelatedObject',
                                   related_name='+')


class RelProxyRelatedObjects(models.Model):
    rel_hidden = models.ForeignKey('ProxyRelatedObject')


class RelProxyHiddenRelatedObjects(models.Model):
    rel_hidden = models.ForeignKey('ProxyRelatedObject',
                                   related_name='+')


# RELATED_OBJECTS MODELS
class BaseRelatedObject(models.Model):
    pass


class RelatedObject(BaseRelatedObject):
    pass


class HiddenRelatedObject(RelatedObject):
    pass


class ProxyRelatedObject(RelatedObject):
    class Meta:
        proxy = True


# RELATED_M2M
# RELATED_M2M RELATIONS
class RelBaseRelatedM2M(models.Model):
    rel_base = models.ManyToManyField('BaseRelatedM2M')


class RelRelatedM2M(models.Model):
    rel = models.ManyToManyField('RelatedM2M')


# RELATED_M2M MODELS
class BaseRelatedM2M(models.Model):
    pass


class RelatedM2M(BaseRelatedM2M):
    pass


# VIRTUAL FIELDS
class ModelWithGenericFK(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')


class AGenericRelation(models.Model):
    generic_model = GenericRelation(ModelWithGenericFK)

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


class Country(models.Model):
    name = models.CharField(max_length=50)


class Person(models.Model):
    name = models.CharField(max_length=10)
    person_country = models.ForeignObject(Country,
        from_fields=['person_country_id'], to_fields=['id'])


@python_2_unicode_compatible
class Musician(models.Model):
    name = models.CharField(max_length=30)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Group(models.Model):
    name = models.CharField(max_length=30)
    members = models.ManyToManyField(Musician)

    def __str__(self):
        return self.name


class Quartet(Group):
    pass


@python_2_unicode_compatible
class OwnedVenue(models.Model):
    name = models.CharField(max_length=30)
    group = models.ForeignKey(Group)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Reporter(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    raw_data = models.BinaryField()

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)


class ReporterProxy(Reporter):
    class Meta:
        proxy = True


@python_2_unicode_compatible
class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateField()
    reporter = models.ForeignKey(Reporter)
    reporter_proxy = models.ForeignKey(ReporterProxy, null=True,
                                       related_name='reporter_proxy')

    def __str__(self):
        return self.headline

# DATA
class AbstractData(models.Model):
    class Meta:
        abstract = True
    name = models.CharField(max_length=10)
    origin = models.ForeignObject(Country,
        from_fields=['person_country_id'], to_fields=['id'])


class Data(AbstractData):
    name_data = models.CharField(max_length=10)


class SuperData(Data):
    name_super_data = models.CharField(max_length=10)
    surname_super_data = models.CharField(max_length=10)
    origin_super_data = models.ForeignObject(Reporter,
        from_fields=['person_country_id'], to_fields=['id'])


# M2M
class AnotherSuperModel(models.Model):
    name_super_m2m = models.CharField(max_length=10)


class AnotherModel(models.Model):
    name_m2m = models.CharField(max_length=10)


class M2MModel(models.Model):
    name_m2m = models.CharField(max_length=10)
    members = models.ManyToManyField(AnotherModel)


class SuperM2MModel(M2MModel):
    members_super = models.ManyToManyField(AnotherSuperModel)


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

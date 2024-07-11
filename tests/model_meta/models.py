from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


class Relation(models.Model):
    pass


class InstanceOnlyDescriptor:
    def __get__(self, instance, cls=None):
        if instance is None:
            raise AttributeError("Instance only")
        return 1


class AbstractPerson(models.Model):
    # DATA fields
    data_abstract = models.CharField(max_length=10)
    fk_abstract = models.ForeignKey(
        Relation, models.CASCADE, related_name="fk_abstract_rel"
    )

    # M2M fields
    m2m_abstract = models.ManyToManyField(Relation, related_name="m2m_abstract_rel")
    friends_abstract = models.ManyToManyField("self", symmetrical=True)
    following_abstract = models.ManyToManyField(
        "self", related_name="followers_abstract", symmetrical=False
    )

    # VIRTUAL fields
    data_not_concrete_abstract = models.ForeignObject(
        Relation,
        on_delete=models.CASCADE,
        from_fields=["abstract_non_concrete_id"],
        to_fields=["id"],
        related_name="fo_abstract_rel",
    )

    # GFK fields
    content_type_abstract = models.ForeignKey(
        ContentType, models.CASCADE, related_name="+"
    )
    object_id_abstract = models.PositiveIntegerField()
    content_object_abstract = GenericForeignKey(
        "content_type_abstract", "object_id_abstract"
    )

    # GR fields
    generic_relation_abstract = GenericRelation(Relation)

    class Meta:
        abstract = True

    @property
    def test_property(self):
        return 1

    test_instance_only_descriptor = InstanceOnlyDescriptor()


class BasePerson(AbstractPerson):
    # DATA fields
    data_base = models.CharField(max_length=10)
    fk_base = models.ForeignKey(Relation, models.CASCADE, related_name="fk_base_rel")

    # M2M fields
    m2m_base = models.ManyToManyField(Relation, related_name="m2m_base_rel")
    friends_base = models.ManyToManyField("self", symmetrical=True)
    following_base = models.ManyToManyField(
        "self", related_name="followers_base", symmetrical=False
    )

    # VIRTUAL fields
    data_not_concrete_base = models.ForeignObject(
        Relation,
        on_delete=models.CASCADE,
        from_fields=["base_non_concrete_id"],
        to_fields=["id"],
        related_name="fo_base_rel",
    )

    # GFK fields
    content_type_base = models.ForeignKey(ContentType, models.CASCADE, related_name="+")
    object_id_base = models.PositiveIntegerField()
    content_object_base = GenericForeignKey("content_type_base", "object_id_base")

    # GR fields
    generic_relation_base = GenericRelation(Relation)


class Person(BasePerson):
    # DATA fields
    data_inherited = models.CharField(max_length=10)
    fk_inherited = models.ForeignKey(
        Relation, models.CASCADE, related_name="fk_concrete_rel"
    )

    # M2M Fields
    m2m_inherited = models.ManyToManyField(Relation, related_name="m2m_concrete_rel")
    friends_inherited = models.ManyToManyField("self", symmetrical=True)
    following_inherited = models.ManyToManyField(
        "self", related_name="followers_concrete", symmetrical=False
    )

    # VIRTUAL fields
    data_not_concrete_inherited = models.ForeignObject(
        Relation,
        on_delete=models.CASCADE,
        from_fields=["model_non_concrete_id"],
        to_fields=["id"],
        related_name="fo_concrete_rel",
    )

    # GFK fields
    content_type_concrete = models.ForeignKey(
        ContentType, models.CASCADE, related_name="+"
    )
    object_id_concrete = models.PositiveIntegerField()
    content_object_concrete = GenericForeignKey(
        "content_type_concrete", "object_id_concrete"
    )

    # GR fields
    generic_relation_concrete = GenericRelation(Relation)

    class Meta:
        verbose_name = _("Person")


class ProxyPerson(Person):
    class Meta:
        proxy = True


class PersonThroughProxySubclass(ProxyPerson):
    pass


class Relating(models.Model):
    # ForeignKey to BasePerson
    baseperson = models.ForeignKey(
        BasePerson, models.CASCADE, related_name="relating_baseperson"
    )
    baseperson_hidden = models.ForeignKey(BasePerson, models.CASCADE, related_name="+")

    # ForeignKey to Person
    person = models.ForeignKey(Person, models.CASCADE, related_name="relating_person")
    person_hidden = models.ForeignKey(Person, models.CASCADE, related_name="+")

    # ForeignKey to ProxyPerson
    proxyperson = models.ForeignKey(
        ProxyPerson, models.CASCADE, related_name="relating_proxyperson"
    )
    proxyperson_hidden = models.ForeignKey(
        ProxyPerson, models.CASCADE, related_name="relating_proxyperson_hidden+"
    )

    # ManyToManyField to BasePerson
    basepeople = models.ManyToManyField(BasePerson, related_name="relating_basepeople")
    basepeople_hidden = models.ManyToManyField(BasePerson, related_name="+")

    # ManyToManyField to Person
    people = models.ManyToManyField(Person, related_name="relating_people")
    people_hidden = models.ManyToManyField(Person, related_name="+")


class Swappable(models.Model):
    class Meta:
        swappable = "MODEL_META_TESTS_SWAPPED"


# ParentListTests models
class CommonAncestor(models.Model):
    pass


class FirstParent(CommonAncestor):
    first_ancestor = models.OneToOneField(
        CommonAncestor, models.CASCADE, primary_key=True, parent_link=True
    )


class SecondParent(CommonAncestor):
    second_ancestor = models.OneToOneField(
        CommonAncestor, models.CASCADE, primary_key=True, parent_link=True
    )


class Child(FirstParent, SecondParent):
    pass

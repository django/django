from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models

__all__ = (
    "Link",
    "Place",
    "Restaurant",
    "Person",
    "Address",
    "CharLink",
    "TextLink",
    "OddRelation1",
    "OddRelation2",
    "Contact",
    "Organization",
    "Note",
    "Company",
)


class Link(models.Model):
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()


class LinkProxy(Link):
    class Meta:
        proxy = True


class Place(models.Model):
    name = models.CharField(max_length=100)
    links = GenericRelation(Link, related_query_name="places")
    link_proxy = GenericRelation(LinkProxy)


class Restaurant(Place):
    pass


class Cafe(Restaurant):
    pass


class Address(models.Model):
    street = models.CharField(max_length=80)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=2)
    zipcode = models.CharField(max_length=5)
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()


class Person(models.Model):
    account = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=128)
    addresses = GenericRelation(Address)


class CharLink(models.Model):
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.CharField(max_length=100)
    content_object = GenericForeignKey()


class TextLink(models.Model):
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.TextField()
    content_object = GenericForeignKey()


class OddRelation1(models.Model):
    name = models.CharField(max_length=100)
    clinks = GenericRelation(CharLink)


class OddRelation2(models.Model):
    name = models.CharField(max_length=100)
    tlinks = GenericRelation(TextLink)


# models for test_q_object_or:
class Note(models.Model):
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()
    note = models.TextField()


class Contact(models.Model):
    notes = GenericRelation(Note)


class Organization(models.Model):
    name = models.CharField(max_length=255)
    contacts = models.ManyToManyField(Contact, related_name="organizations")


class Company(models.Model):
    name = models.CharField(max_length=100)
    links = GenericRelation(Link)


# For testing #13085 fix, we also use Note model defined above
class Developer(models.Model):
    name = models.CharField(max_length=15)


class Team(models.Model):
    name = models.CharField(max_length=15)
    members = models.ManyToManyField(Developer)

    def __len__(self):
        return self.members.count()


class Guild(models.Model):
    name = models.CharField(max_length=15)
    members = models.ManyToManyField(Developer)

    def __bool__(self):
        return False


class Tag(models.Model):
    content_type = models.ForeignKey(
        ContentType, models.CASCADE, related_name="g_r_r_tags"
    )
    object_id = models.CharField(max_length=15)
    content_object = GenericForeignKey()
    label = models.CharField(max_length=15)


class Board(models.Model):
    name = models.CharField(primary_key=True, max_length=25)


class SpecialGenericRelation(GenericRelation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.editable = True
        self.save_form_data_calls = 0

    def save_form_data(self, *args, **kwargs):
        self.save_form_data_calls += 1


class HasLinks(models.Model):
    links = SpecialGenericRelation(Link, related_query_name="targets")

    class Meta:
        abstract = True


class HasLinkThing(HasLinks):
    pass


class A(models.Model):
    flag = models.BooleanField(null=True)
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")


class B(models.Model):
    a = GenericRelation(A)

    class Meta:
        ordering = ("id",)


class C(models.Model):
    b = models.ForeignKey(B, models.CASCADE)

    class Meta:
        ordering = ("id",)


class D(models.Model):
    b = models.ForeignKey(B, models.SET_NULL, null=True)

    class Meta:
        ordering = ("id",)


# Ticket #22998


class Node(models.Model):
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()
    content = GenericForeignKey("content_type", "object_id")


class Content(models.Model):
    nodes = GenericRelation(Node)
    related_obj = models.ForeignKey("Related", models.CASCADE)


class Related(models.Model):
    pass


def prevent_deletes(sender, instance, **kwargs):
    raise models.ProtectedError("Not allowed to delete.", [instance])


models.signals.pre_delete.connect(prevent_deletes, sender=Node)

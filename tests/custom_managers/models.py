"""
Giving models a custom manager

You can use a custom ``Manager`` in a particular model by extending the base
``Manager`` class and instantiating your custom ``Manager`` in your model.

There are two reasons you might want to customize a ``Manager``: to add extra
``Manager`` methods, and/or to modify the initial ``QuerySet`` the ``Manager``
returns.
"""

from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.db import models


class PersonManager(models.Manager):
    def get_fun_people(self):
        return self.filter(fun=True)


class PublishedBookManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)


class AnnotatedBookManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().annotate(
            favorite_avg=models.Avg('favorite_books__favorite_thing_id')
        )


class CustomQuerySet(models.QuerySet):
    def filter(self, *args, **kwargs):
        queryset = super().filter(fun=True)
        queryset._filter_CustomQuerySet = True
        return queryset

    def public_method(self, *args, **kwargs):
        return self.all()

    def _private_method(self, *args, **kwargs):
        return self.all()

    def optout_public_method(self, *args, **kwargs):
        return self.all()
    optout_public_method.queryset_only = True

    def _optin_private_method(self, *args, **kwargs):
        return self.all()
    _optin_private_method.queryset_only = False


class BaseCustomManager(models.Manager):
    def __init__(self, arg):
        super().__init__()
        self.init_arg = arg

    def filter(self, *args, **kwargs):
        queryset = super().filter(fun=True)
        queryset._filter_CustomManager = True
        return queryset

    def manager_only(self):
        return self.all()


CustomManager = BaseCustomManager.from_queryset(CustomQuerySet)


class CustomInitQuerySet(models.QuerySet):
    # QuerySet with an __init__() method that takes an additional argument.
    def __init__(self, custom_optional_arg=None, model=None, query=None, using=None, hints=None):
        super().__init__(model=model, query=query, using=using, hints=hints)


class DeconstructibleCustomManager(BaseCustomManager.from_queryset(CustomQuerySet)):

    def __init__(self, a, b, c=1, d=2):
        super().__init__(a)


class FunPeopleManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(fun=True)


class BoringPeopleManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(fun=False)


class Person(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    fun = models.BooleanField(default=False)

    favorite_book = models.ForeignKey('Book', models.SET_NULL, null=True, related_name='favorite_books')
    favorite_thing_type = models.ForeignKey('contenttypes.ContentType', models.SET_NULL, null=True)
    favorite_thing_id = models.IntegerField(null=True)
    favorite_thing = GenericForeignKey('favorite_thing_type', 'favorite_thing_id')

    objects = PersonManager()
    fun_people = FunPeopleManager()
    boring_people = BoringPeopleManager()

    custom_queryset_default_manager = CustomQuerySet.as_manager()
    custom_queryset_custom_manager = CustomManager('hello')
    custom_init_queryset_manager = CustomInitQuerySet.as_manager()

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)


class FunPerson(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    fun = models.BooleanField(default=True)
    favorite_book = models.ForeignKey(
        'Book',
        models.SET_NULL,
        null=True,
        related_name='fun_people_favorite_books',
    )
    favorite_thing_type = models.ForeignKey('contenttypes.ContentType', models.SET_NULL, null=True)
    favorite_thing_id = models.IntegerField(null=True)
    favorite_thing = GenericForeignKey('favorite_thing_type', 'favorite_thing_id')

    objects = FunPeopleManager()

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)


class Book(models.Model):
    title = models.CharField(max_length=50)
    author = models.CharField(max_length=30)
    is_published = models.BooleanField(default=False)
    authors = models.ManyToManyField(Person, related_name='books')
    fun_authors = models.ManyToManyField(FunPerson, related_name='books')
    favorite_things = GenericRelation(
        Person,
        content_type_field='favorite_thing_type',
        object_id_field='favorite_thing_id',
    )
    fun_people_favorite_things = GenericRelation(
        FunPerson,
        content_type_field='favorite_thing_type',
        object_id_field='favorite_thing_id',
    )

    published_objects = PublishedBookManager()
    annotated_objects = AnnotatedBookManager()

    class Meta:
        base_manager_name = 'annotated_objects'

    def __str__(self):
        return self.title


class FastCarManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(top_speed__gt=150)


class Car(models.Model):
    name = models.CharField(max_length=10)
    mileage = models.IntegerField()
    top_speed = models.IntegerField(help_text="In miles per hour.")
    cars = models.Manager()
    fast_cars = FastCarManager()

    def __str__(self):
        return self.name


class FastCarAsBase(Car):
    class Meta:
        proxy = True
        base_manager_name = 'fast_cars'


class FastCarAsDefault(Car):
    class Meta:
        proxy = True
        default_manager_name = 'fast_cars'


class RestrictedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_public=True)


class RelatedModel(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class RestrictedModel(models.Model):
    name = models.CharField(max_length=50)
    is_public = models.BooleanField(default=False)
    related = models.ForeignKey(RelatedModel, models.CASCADE)

    objects = RestrictedManager()
    plain_manager = models.Manager()

    def __str__(self):
        return self.name


class OneToOneRestrictedModel(models.Model):
    name = models.CharField(max_length=50)
    is_public = models.BooleanField(default=False)
    related = models.OneToOneField(RelatedModel, models.CASCADE)

    objects = RestrictedManager()
    plain_manager = models.Manager()

    def __str__(self):
        return self.name


class AbstractPerson(models.Model):
    abstract_persons = models.Manager()
    objects = models.CharField(max_length=30)

    class Meta:
        abstract = True


class PersonFromAbstract(AbstractPerson):
    pass

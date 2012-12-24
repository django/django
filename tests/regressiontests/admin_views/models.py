# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import tempfile
import os

from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


class Section(models.Model):
    """
    A simple section that links to articles, to test linking to related items
    in admin views.
    """
    name = models.CharField(max_length=100)


@python_2_unicode_compatible
class Article(models.Model):
    """
    A simple article to test admin views. Test backwards compatibility.
    """
    title = models.CharField(max_length=100)
    content = models.TextField()
    date = models.DateTimeField()
    section = models.ForeignKey(Section, null=True, blank=True)

    def __str__(self):
        return self.title

    def model_year(self):
        return self.date.year
    model_year.admin_order_field = 'date'
    model_year.short_description = ''


@python_2_unicode_compatible
class Book(models.Model):
    """
    A simple book that has chapters.
    """
    name = models.CharField(max_length=100, verbose_name='¿Name?')

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Promo(models.Model):
    name = models.CharField(max_length=100, verbose_name='¿Name?')
    book = models.ForeignKey(Book)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Chapter(models.Model):
    title = models.CharField(max_length=100, verbose_name='¿Title?')
    content = models.TextField()
    book = models.ForeignKey(Book)

    def __str__(self):
        return self.title

    class Meta:
        # Use a utf-8 bytestring to ensure it works (see #11710)
        verbose_name = '¿Chapter?'


@python_2_unicode_compatible
class ChapterXtra1(models.Model):
    chap = models.OneToOneField(Chapter, verbose_name='¿Chap?')
    xtra = models.CharField(max_length=100, verbose_name='¿Xtra?')

    def __str__(self):
        return '¿Xtra1: %s' % self.xtra


@python_2_unicode_compatible
class ChapterXtra2(models.Model):
    chap = models.OneToOneField(Chapter, verbose_name='¿Chap?')
    xtra = models.CharField(max_length=100, verbose_name='¿Xtra?')

    def __str__(self):
        return '¿Xtra2: %s' % self.xtra


class RowLevelChangePermissionModel(models.Model):
    name = models.CharField(max_length=100, blank=True)


class CustomArticle(models.Model):
    content = models.TextField()
    date = models.DateTimeField()


@python_2_unicode_compatible
class ModelWithStringPrimaryKey(models.Model):
    string_pk = models.CharField(max_length=255, primary_key=True)

    def __str__(self):
        return self.string_pk

    def get_absolute_url(self):
        return '/dummy/%s/' % self.string_pk


@python_2_unicode_compatible
class Color(models.Model):
    value = models.CharField(max_length=10)
    warm = models.BooleanField()
    def __str__(self):
        return self.value

# we replicate Color to register with another ModelAdmin
class Color2(Color):
    class Meta:
        proxy = True

@python_2_unicode_compatible
class Thing(models.Model):
    title = models.CharField(max_length=20)
    color = models.ForeignKey(Color, limit_choices_to={'warm': True})
    pub_date = models.DateField(blank=True, null=True)
    def __str__(self):
        return self.title


@python_2_unicode_compatible
class Actor(models.Model):
    name = models.CharField(max_length=50)
    age = models.IntegerField()
    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Inquisition(models.Model):
    expected = models.BooleanField()
    leader = models.ForeignKey(Actor)
    country = models.CharField(max_length=20)

    def __str__(self):
        return "by %s from %s" % (self.leader, self.country)


@python_2_unicode_compatible
class Sketch(models.Model):
    title = models.CharField(max_length=100)
    inquisition = models.ForeignKey(Inquisition, limit_choices_to={'leader__name': 'Palin',
                                                                   'leader__age': 27,
                                                                   'expected': False,
                                                                   })

    def __str__(self):
        return self.title


class Fabric(models.Model):
    NG_CHOICES = (
        ('Textured', (
                ('x', 'Horizontal'),
                ('y', 'Vertical'),
            )
        ),
        ('plain', 'Smooth'),
    )
    surface = models.CharField(max_length=20, choices=NG_CHOICES)


@python_2_unicode_compatible
class Person(models.Model):
    GENDER_CHOICES = (
        (1, "Male"),
        (2, "Female"),
    )
    name = models.CharField(max_length=100)
    gender = models.IntegerField(choices=GENDER_CHOICES)
    age = models.IntegerField(default=21)
    alive = models.BooleanField()

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Persona(models.Model):
    """
    A simple persona associated with accounts, to test inlining of related
    accounts which inherit from a common accounts class.
    """
    name = models.CharField(blank=False,  max_length=80)
    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Account(models.Model):
    """
    A simple, generic account encapsulating the information shared by all
    types of accounts.
    """
    username = models.CharField(blank=False,  max_length=80)
    persona = models.ForeignKey(Persona, related_name="accounts")
    servicename = 'generic service'

    def __str__(self):
        return "%s: %s" % (self.servicename, self.username)


class FooAccount(Account):
    """A service-specific account of type Foo."""
    servicename = 'foo'


class BarAccount(Account):
    """A service-specific account of type Bar."""
    servicename = 'bar'


@python_2_unicode_compatible
class Subscriber(models.Model):
    name = models.CharField(blank=False, max_length=80)
    email = models.EmailField(blank=False, max_length=175)

    def __str__(self):
        return "%s (%s)" % (self.name, self.email)


class ExternalSubscriber(Subscriber):
    pass


class OldSubscriber(Subscriber):
    pass


class Media(models.Model):
    name = models.CharField(max_length=60)


class Podcast(Media):
    release_date = models.DateField()

    class Meta:
        ordering = ('release_date',) # overridden in PodcastAdmin


class Vodcast(Media):
    media = models.OneToOneField(Media, primary_key=True, parent_link=True)
    released = models.BooleanField(default=False)


class Parent(models.Model):
    name = models.CharField(max_length=128)


class Child(models.Model):
    parent = models.ForeignKey(Parent, editable=False)
    name = models.CharField(max_length=30, blank=True)


@python_2_unicode_compatible
class EmptyModel(models.Model):
    def __str__(self):
        return "Primary key = %s" % self.id


temp_storage = FileSystemStorage(tempfile.mkdtemp(dir=os.environ['DJANGO_TEST_TEMP_DIR']))
UPLOAD_TO = os.path.join(temp_storage.location, 'test_upload')


class Gallery(models.Model):
    name = models.CharField(max_length=100)


class Picture(models.Model):
    name = models.CharField(max_length=100)
    image = models.FileField(storage=temp_storage, upload_to='test_upload')
    gallery = models.ForeignKey(Gallery, related_name="pictures")


class Language(models.Model):
    iso = models.CharField(max_length=5, primary_key=True)
    name = models.CharField(max_length=50)
    english_name = models.CharField(max_length=50)
    shortlist = models.BooleanField(default=False)

    class Meta:
        ordering = ('iso',)


# a base class for Recommender and Recommendation
class Title(models.Model):
    pass


class TitleTranslation(models.Model):
    title = models.ForeignKey(Title)
    text = models.CharField(max_length=100)


class Recommender(Title):
    pass


class Recommendation(Title):
    recommender = models.ForeignKey(Recommender)


class Collector(models.Model):
    name = models.CharField(max_length=100)


class Widget(models.Model):
    owner = models.ForeignKey(Collector)
    name = models.CharField(max_length=100)


class DooHickey(models.Model):
    code = models.CharField(max_length=10, primary_key=True)
    owner = models.ForeignKey(Collector)
    name = models.CharField(max_length=100)


class Grommet(models.Model):
    code = models.AutoField(primary_key=True)
    owner = models.ForeignKey(Collector)
    name = models.CharField(max_length=100)


class Whatsit(models.Model):
    index = models.IntegerField(primary_key=True)
    owner = models.ForeignKey(Collector)
    name = models.CharField(max_length=100)


class Doodad(models.Model):
    name = models.CharField(max_length=100)


class FancyDoodad(Doodad):
    owner = models.ForeignKey(Collector)
    expensive = models.BooleanField(default=True)


@python_2_unicode_compatible
class Category(models.Model):
    collector = models.ForeignKey(Collector)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ('order',)

    def __str__(self):
        return '%s:o%s' % (self.id, self.order)


class Link(models.Model):
    posted = models.DateField(
        default=lambda: datetime.date.today() - datetime.timedelta(days=7)
    )
    url = models.URLField()
    post = models.ForeignKey("Post")


class PrePopulatedPost(models.Model):
    title = models.CharField(max_length=100)
    published = models.BooleanField()
    slug = models.SlugField()


class PrePopulatedSubPost(models.Model):
    post = models.ForeignKey(PrePopulatedPost)
    subtitle = models.CharField(max_length=100)
    subslug = models.SlugField()


class Post(models.Model):
    title = models.CharField(max_length=100, help_text="Some help text for the title (with unicode ŠĐĆŽćžšđ)")
    content = models.TextField(help_text="Some help text for the content (with unicode ŠĐĆŽćžšđ)")
    posted = models.DateField(
            default=datetime.date.today,
            help_text="Some help text for the date (with unicode ŠĐĆŽćžšđ)"
    )
    public = models.NullBooleanField()

    def awesomeness_level(self):
        return "Very awesome."


@python_2_unicode_compatible
class Gadget(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Villain(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class SuperVillain(Villain):
    pass


@python_2_unicode_compatible
class FunkyTag(models.Model):
    "Because we all know there's only one real use case for GFKs."
    name = models.CharField(max_length=25)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Plot(models.Model):
    name = models.CharField(max_length=100)
    team_leader = models.ForeignKey(Villain, related_name='lead_plots')
    contact = models.ForeignKey(Villain, related_name='contact_plots')
    tags = generic.GenericRelation(FunkyTag)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class PlotDetails(models.Model):
    details = models.CharField(max_length=100)
    plot = models.OneToOneField(Plot)

    def __str__(self):
        return self.details


@python_2_unicode_compatible
class SecretHideout(models.Model):
    """ Secret! Not registered with the admin! """
    location = models.CharField(max_length=100)
    villain = models.ForeignKey(Villain)

    def __str__(self):
        return self.location


@python_2_unicode_compatible
class SuperSecretHideout(models.Model):
    """ Secret! Not registered with the admin! """
    location = models.CharField(max_length=100)
    supervillain = models.ForeignKey(SuperVillain)

    def __str__(self):
        return self.location


@python_2_unicode_compatible
class CyclicOne(models.Model):
    name = models.CharField(max_length=25)
    two = models.ForeignKey('CyclicTwo')

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class CyclicTwo(models.Model):
    name = models.CharField(max_length=25)
    one = models.ForeignKey(CyclicOne)

    def __str__(self):
        return self.name


class Topping(models.Model):
    name = models.CharField(max_length=20)


class Pizza(models.Model):
    name = models.CharField(max_length=20)
    toppings = models.ManyToManyField('Topping')


class Album(models.Model):
    owner = models.ForeignKey(User)
    title = models.CharField(max_length=30)


class Employee(Person):
    code = models.CharField(max_length=20)


class WorkHour(models.Model):
    datum = models.DateField()
    employee = models.ForeignKey(Employee)


class Question(models.Model):
    question = models.CharField(max_length=20)


@python_2_unicode_compatible
class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    answer = models.CharField(max_length=20)

    def __str__(self):
        return self.answer


class Reservation(models.Model):
    start_date = models.DateTimeField()
    price = models.IntegerField()


DRIVER_CHOICES = (
    ('bill', 'Bill G'),
    ('steve', 'Steve J'),
)

RESTAURANT_CHOICES = (
    ('indian', 'A Taste of India'),
    ('thai', 'Thai Pography'),
    ('pizza', 'Pizza Mama'),
)


class FoodDelivery(models.Model):
    reference = models.CharField(max_length=100)
    driver = models.CharField(max_length=100, choices=DRIVER_CHOICES, blank=True)
    restaurant = models.CharField(max_length=100, choices=RESTAURANT_CHOICES, blank=True)

    class Meta:
        unique_together = (("driver", "restaurant"),)


@python_2_unicode_compatible
class CoverLetter(models.Model):
    author = models.CharField(max_length=30)
    date_written = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.author


class Paper(models.Model):
    title = models.CharField(max_length=30)
    author = models.CharField(max_length=30, blank=True, null=True)


class ShortMessage(models.Model):
    content = models.CharField(max_length=140)
    timestamp = models.DateTimeField(null=True, blank=True)


@python_2_unicode_compatible
class Telegram(models.Model):
    title = models.CharField(max_length=30)
    date_sent = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.title


class Story(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()


class OtherStory(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()


class ComplexSortedPerson(models.Model):
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    is_employee = models.NullBooleanField()

class PrePopulatedPostLargeSlug(models.Model):
    """
    Regression test for #15938: a large max_length for the slugfield must not
    be localized in prepopulated_fields_js.html or it might end up breaking
    the javascript (ie, using THOUSAND_SEPARATOR ends up with maxLength=1,000)
    """
    title = models.CharField(max_length=100)
    published = models.BooleanField()
    slug = models.SlugField(max_length=1000)

class AdminOrderedField(models.Model):
    order = models.IntegerField()
    stuff = models.CharField(max_length=200)

class AdminOrderedModelMethod(models.Model):
    order = models.IntegerField()
    stuff = models.CharField(max_length=200)
    def some_order(self):
        return self.order
    some_order.admin_order_field = 'order'

class AdminOrderedAdminMethod(models.Model):
    order = models.IntegerField()
    stuff = models.CharField(max_length=200)

class AdminOrderedCallable(models.Model):
    order = models.IntegerField()
    stuff = models.CharField(max_length=200)

@python_2_unicode_compatible
class Report(models.Model):
    title = models.CharField(max_length=100)

    def __str__(self):
        return self.title


class MainPrepopulated(models.Model):
    name = models.CharField(max_length=100)
    pubdate = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=(('option one', 'Option One'),
                 ('option two', 'Option Two')))
    slug1 = models.SlugField()
    slug2 = models.SlugField()

class RelatedPrepopulated(models.Model):
    parent = models.ForeignKey(MainPrepopulated)
    name = models.CharField(max_length=75)
    pubdate = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=(('option one', 'Option One'),
                 ('option two', 'Option Two')))
    slug1 = models.SlugField(max_length=50)
    slug2 = models.SlugField(max_length=60)


class UnorderedObject(models.Model):
    """
    Model without any defined `Meta.ordering`.
    Refs #16819.
    """
    name = models.CharField(max_length=255)
    bool = models.BooleanField(default=True)

class UndeletableObject(models.Model):
    """
    Model whose show_delete in admin change_view has been disabled
    Refs #10057.
    """
    name = models.CharField(max_length=255)

class UserMessenger(models.Model):
    """
    Dummy class for testing message_user functions on ModelAdmin
    """

class Simple(models.Model):
    """
    Simple model with nothing on it for use in testing
    """

class Choice(models.Model):
    choice = models.IntegerField(blank=True, null=True,
        choices=((1, 'Yes'), (0, 'No'), (None, 'No opinion')))

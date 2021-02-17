import datetime
import os
import tempfile
import uuid

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models


class Section(models.Model):
    """
    A simple section that links to articles, to test linking to related items
    in admin views.
    """
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    @property
    def name_property(self):
        """
        A property that simply returns the name. Used to test #24461
        """
        return self.name


class Article(models.Model):
    """
    A simple article to test admin views. Test backwards compatibility.
    """
    title = models.CharField(max_length=100)
    content = models.TextField()
    date = models.DateTimeField()
    section = models.ForeignKey(Section, models.CASCADE, null=True, blank=True)
    another_section = models.ForeignKey(Section, models.CASCADE, null=True, blank=True, related_name='+')
    sub_section = models.ForeignKey(Section, models.SET_NULL, null=True, blank=True, related_name='+')

    def __str__(self):
        return self.title

    @admin.display(ordering='date', description='')
    def model_year(self):
        return self.date.year

    @admin.display(ordering='-date', description='')
    def model_year_reversed(self):
        return self.date.year

    @property
    @admin.display(ordering='date')
    def model_property_year(self):
        return self.date.year

    @property
    def model_month(self):
        return self.date.month


class Book(models.Model):
    """
    A simple book that has chapters.
    """
    name = models.CharField(max_length=100, verbose_name='¿Name?')

    def __str__(self):
        return self.name


class Promo(models.Model):
    name = models.CharField(max_length=100, verbose_name='¿Name?')
    book = models.ForeignKey(Book, models.CASCADE)
    author = models.ForeignKey(User, models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return self.name


class Chapter(models.Model):
    title = models.CharField(max_length=100, verbose_name='¿Title?')
    content = models.TextField()
    book = models.ForeignKey(Book, models.CASCADE)

    class Meta:
        # Use a utf-8 bytestring to ensure it works (see #11710)
        verbose_name = '¿Chapter?'

    def __str__(self):
        return self.title


class ChapterXtra1(models.Model):
    chap = models.OneToOneField(Chapter, models.CASCADE, verbose_name='¿Chap?')
    xtra = models.CharField(max_length=100, verbose_name='¿Xtra?')
    guest_author = models.ForeignKey(User, models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return '¿Xtra1: %s' % self.xtra


class ChapterXtra2(models.Model):
    chap = models.OneToOneField(Chapter, models.CASCADE, verbose_name='¿Chap?')
    xtra = models.CharField(max_length=100, verbose_name='¿Xtra?')

    def __str__(self):
        return '¿Xtra2: %s' % self.xtra


class RowLevelChangePermissionModel(models.Model):
    name = models.CharField(max_length=100, blank=True)


class CustomArticle(models.Model):
    content = models.TextField()
    date = models.DateTimeField()


class ModelWithStringPrimaryKey(models.Model):
    string_pk = models.CharField(max_length=255, primary_key=True)

    def __str__(self):
        return self.string_pk

    def get_absolute_url(self):
        return '/dummy/%s/' % self.string_pk


class Color(models.Model):
    value = models.CharField(max_length=10)
    warm = models.BooleanField(default=False)

    def __str__(self):
        return self.value


# we replicate Color to register with another ModelAdmin
class Color2(Color):
    class Meta:
        proxy = True


class Thing(models.Model):
    title = models.CharField(max_length=20)
    color = models.ForeignKey(Color, models.CASCADE, limit_choices_to={'warm': True})
    pub_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.title


class Actor(models.Model):
    name = models.CharField(max_length=50)
    age = models.IntegerField()
    title = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.name


class Inquisition(models.Model):
    expected = models.BooleanField(default=False)
    leader = models.ForeignKey(Actor, models.CASCADE)
    country = models.CharField(max_length=20)

    def __str__(self):
        return "by %s from %s" % (self.leader, self.country)


class Sketch(models.Model):
    title = models.CharField(max_length=100)
    inquisition = models.ForeignKey(
        Inquisition,
        models.CASCADE,
        limit_choices_to={
            'leader__name': 'Palin',
            'leader__age': 27,
            'expected': False,
        },
    )
    defendant0 = models.ForeignKey(
        Actor,
        models.CASCADE,
        limit_choices_to={'title__isnull': False},
        related_name='as_defendant0',
    )
    defendant1 = models.ForeignKey(
        Actor,
        models.CASCADE,
        limit_choices_to={'title__isnull': True},
        related_name='as_defendant1',
    )

    def __str__(self):
        return self.title


def today_callable_dict():
    return {"last_action__gte": datetime.datetime.today()}


def today_callable_q():
    return models.Q(last_action__gte=datetime.datetime.today())


class Character(models.Model):
    username = models.CharField(max_length=100)
    last_action = models.DateTimeField()

    def __str__(self):
        return self.username


class StumpJoke(models.Model):
    variation = models.CharField(max_length=100)
    most_recently_fooled = models.ForeignKey(
        Character,
        models.CASCADE,
        limit_choices_to=today_callable_dict,
        related_name="+",
    )
    has_fooled_today = models.ManyToManyField(Character, limit_choices_to=today_callable_q, related_name="+")

    def __str__(self):
        return self.variation


class Fabric(models.Model):
    NG_CHOICES = (
        ('Textured', (
            ('x', 'Horizontal'),
            ('y', 'Vertical'),
        )),
        ('plain', 'Smooth'),
    )
    surface = models.CharField(max_length=20, choices=NG_CHOICES)


class Person(models.Model):
    GENDER_CHOICES = (
        (1, "Male"),
        (2, "Female"),
    )
    name = models.CharField(max_length=100)
    gender = models.IntegerField(choices=GENDER_CHOICES)
    age = models.IntegerField(default=21)
    alive = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Persona(models.Model):
    """
    A simple persona associated with accounts, to test inlining of related
    accounts which inherit from a common accounts class.
    """
    name = models.CharField(blank=False, max_length=80)

    def __str__(self):
        return self.name


class Account(models.Model):
    """
    A simple, generic account encapsulating the information shared by all
    types of accounts.
    """
    username = models.CharField(blank=False, max_length=80)
    persona = models.ForeignKey(Persona, models.CASCADE, related_name="accounts")
    servicename = 'generic service'

    def __str__(self):
        return "%s: %s" % (self.servicename, self.username)


class FooAccount(Account):
    """A service-specific account of type Foo."""
    servicename = 'foo'


class BarAccount(Account):
    """A service-specific account of type Bar."""
    servicename = 'bar'


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
        ordering = ('release_date',)  # overridden in PodcastAdmin


class Vodcast(Media):
    media = models.OneToOneField(Media, models.CASCADE, primary_key=True, parent_link=True)
    released = models.BooleanField(default=False)


class Parent(models.Model):
    name = models.CharField(max_length=128)

    def clean(self):
        if self.name == '_invalid':
            raise ValidationError('invalid')


class Child(models.Model):
    parent = models.ForeignKey(Parent, models.CASCADE, editable=False)
    name = models.CharField(max_length=30, blank=True)

    def clean(self):
        if self.name == '_invalid':
            raise ValidationError('invalid')


class EmptyModel(models.Model):
    def __str__(self):
        return "Primary key = %s" % self.id


temp_storage = FileSystemStorage(tempfile.mkdtemp())
UPLOAD_TO = os.path.join(temp_storage.location, 'test_upload')


class Gallery(models.Model):
    name = models.CharField(max_length=100)


class Picture(models.Model):
    name = models.CharField(max_length=100)
    image = models.FileField(storage=temp_storage, upload_to='test_upload')
    gallery = models.ForeignKey(Gallery, models.CASCADE, related_name="pictures")


class Language(models.Model):
    iso = models.CharField(max_length=5, primary_key=True)
    name = models.CharField(max_length=50)
    english_name = models.CharField(max_length=50)
    shortlist = models.BooleanField(default=False)

    def __str__(self):
        return self.iso

    class Meta:
        ordering = ('iso',)


# a base class for Recommender and Recommendation
class Title(models.Model):
    pass


class TitleTranslation(models.Model):
    title = models.ForeignKey(Title, models.CASCADE)
    text = models.CharField(max_length=100)


class Recommender(Title):
    pass


class Recommendation(Title):
    the_recommender = models.ForeignKey(Recommender, models.CASCADE)


class Collector(models.Model):
    name = models.CharField(max_length=100)


class Widget(models.Model):
    owner = models.ForeignKey(Collector, models.CASCADE)
    name = models.CharField(max_length=100)


class DooHickey(models.Model):
    code = models.CharField(max_length=10, primary_key=True)
    owner = models.ForeignKey(Collector, models.CASCADE)
    name = models.CharField(max_length=100)


class Grommet(models.Model):
    code = models.AutoField(primary_key=True)
    owner = models.ForeignKey(Collector, models.CASCADE)
    name = models.CharField(max_length=100)


class Whatsit(models.Model):
    index = models.IntegerField(primary_key=True)
    owner = models.ForeignKey(Collector, models.CASCADE)
    name = models.CharField(max_length=100)


class Doodad(models.Model):
    name = models.CharField(max_length=100)


class FancyDoodad(Doodad):
    owner = models.ForeignKey(Collector, models.CASCADE)
    expensive = models.BooleanField(default=True)


class Category(models.Model):
    collector = models.ForeignKey(Collector, models.CASCADE)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ('order',)

    def __str__(self):
        return '%s:o%s' % (self.id, self.order)


def link_posted_default():
    return datetime.date.today() - datetime.timedelta(days=7)


class Link(models.Model):
    posted = models.DateField(default=link_posted_default)
    url = models.URLField()
    post = models.ForeignKey("Post", models.CASCADE)
    readonly_link_content = models.TextField()


class PrePopulatedPost(models.Model):
    title = models.CharField(max_length=100)
    published = models.BooleanField(default=False)
    slug = models.SlugField()


class PrePopulatedSubPost(models.Model):
    post = models.ForeignKey(PrePopulatedPost, models.CASCADE)
    subtitle = models.CharField(max_length=100)
    subslug = models.SlugField()


class Post(models.Model):
    title = models.CharField(max_length=100, help_text='Some help text for the title (with Unicode ŠĐĆŽćžšđ)')
    content = models.TextField(help_text='Some help text for the content (with Unicode ŠĐĆŽćžšđ)')
    readonly_content = models.TextField()
    posted = models.DateField(
        default=datetime.date.today,
        help_text='Some help text for the date (with Unicode ŠĐĆŽćžšđ)',
    )
    public = models.BooleanField(null=True, blank=True)

    def awesomeness_level(self):
        return "Very awesome."


# Proxy model to test overridden fields attrs on Post model so as not to
# interfere with other tests.
class FieldOverridePost(Post):
    class Meta:
        proxy = True


class Gadget(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Villain(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class SuperVillain(Villain):
    pass


class FunkyTag(models.Model):
    "Because we all know there's only one real use case for GFKs."
    name = models.CharField(max_length=25)
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return self.name


class Plot(models.Model):
    name = models.CharField(max_length=100)
    team_leader = models.ForeignKey(Villain, models.CASCADE, related_name='lead_plots')
    contact = models.ForeignKey(Villain, models.CASCADE, related_name='contact_plots')
    tags = GenericRelation(FunkyTag)

    def __str__(self):
        return self.name


class PlotDetails(models.Model):
    details = models.CharField(max_length=100)
    plot = models.OneToOneField(Plot, models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.details


class PlotProxy(Plot):
    class Meta:
        proxy = True


class SecretHideout(models.Model):
    """ Secret! Not registered with the admin! """
    location = models.CharField(max_length=100)
    villain = models.ForeignKey(Villain, models.CASCADE)

    def __str__(self):
        return self.location


class SuperSecretHideout(models.Model):
    """ Secret! Not registered with the admin! """
    location = models.CharField(max_length=100)
    supervillain = models.ForeignKey(SuperVillain, models.CASCADE)

    def __str__(self):
        return self.location


class Bookmark(models.Model):
    name = models.CharField(max_length=60)
    tag = GenericRelation(FunkyTag, related_query_name='bookmark')

    def __str__(self):
        return self.name


class CyclicOne(models.Model):
    name = models.CharField(max_length=25)
    two = models.ForeignKey('CyclicTwo', models.CASCADE)

    def __str__(self):
        return self.name


class CyclicTwo(models.Model):
    name = models.CharField(max_length=25)
    one = models.ForeignKey(CyclicOne, models.CASCADE)

    def __str__(self):
        return self.name


class Topping(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class Pizza(models.Model):
    name = models.CharField(max_length=20)
    toppings = models.ManyToManyField('Topping', related_name='pizzas')


# Pizza's ModelAdmin has readonly_fields = ['toppings'].
# toppings is editable for this model's admin.
class ReadablePizza(Pizza):
    class Meta:
        proxy = True


# No default permissions are created for this model and both name and toppings
# are readonly for this model's admin.
class ReadOnlyPizza(Pizza):
    class Meta:
        proxy = True
        default_permissions = ()


class Album(models.Model):
    owner = models.ForeignKey(User, models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=30)


class Song(models.Model):
    name = models.CharField(max_length=20)
    album = models.ForeignKey(Album, on_delete=models.RESTRICT)

    def __str__(self):
        return self.name


class Employee(Person):
    code = models.CharField(max_length=20)


class WorkHour(models.Model):
    datum = models.DateField()
    employee = models.ForeignKey(Employee, models.CASCADE)


class Question(models.Model):
    question = models.CharField(max_length=20)
    posted = models.DateField(default=datetime.date.today)
    expires = models.DateTimeField(null=True, blank=True)
    related_questions = models.ManyToManyField('self')
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)

    def __str__(self):
        return self.question


class Answer(models.Model):
    question = models.ForeignKey(Question, models.PROTECT)
    question_with_to_field = models.ForeignKey(
        Question, models.SET_NULL,
        blank=True, null=True, to_field='uuid',
        related_name='uuid_answers',
        limit_choices_to=~models.Q(question__istartswith='not'),
    )
    related_answers = models.ManyToManyField('self')
    answer = models.CharField(max_length=20)

    def __str__(self):
        return self.answer


class Answer2(Answer):
    class Meta:
        proxy = True


class Reservation(models.Model):
    start_date = models.DateTimeField()
    price = models.IntegerField()


class FoodDelivery(models.Model):
    DRIVER_CHOICES = (
        ('bill', 'Bill G'),
        ('steve', 'Steve J'),
    )
    RESTAURANT_CHOICES = (
        ('indian', 'A Taste of India'),
        ('thai', 'Thai Pography'),
        ('pizza', 'Pizza Mama'),
    )
    reference = models.CharField(max_length=100)
    driver = models.CharField(max_length=100, choices=DRIVER_CHOICES, blank=True)
    restaurant = models.CharField(max_length=100, choices=RESTAURANT_CHOICES, blank=True)

    class Meta:
        unique_together = (("driver", "restaurant"),)


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
    is_employee = models.BooleanField(null=True)


class PluggableSearchPerson(models.Model):
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()


class PrePopulatedPostLargeSlug(models.Model):
    """
    Regression test for #15938: a large max_length for the slugfield must not
    be localized in prepopulated_fields_js.html or it might end up breaking
    the javascript (ie, using THOUSAND_SEPARATOR ends up with maxLength=1,000)
    """
    title = models.CharField(max_length=100)
    published = models.BooleanField(default=False)
    # `db_index=False` because MySQL cannot index large CharField (#21196).
    slug = models.SlugField(max_length=1000, db_index=False)


class AdminOrderedField(models.Model):
    order = models.IntegerField()
    stuff = models.CharField(max_length=200)


class AdminOrderedModelMethod(models.Model):
    order = models.IntegerField()
    stuff = models.CharField(max_length=200)

    @admin.display(ordering='order')
    def some_order(self):
        return self.order


class AdminOrderedAdminMethod(models.Model):
    order = models.IntegerField()
    stuff = models.CharField(max_length=200)


class AdminOrderedCallable(models.Model):
    order = models.IntegerField()
    stuff = models.CharField(max_length=200)


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
    slug1 = models.SlugField(blank=True)
    slug2 = models.SlugField(blank=True)
    slug3 = models.SlugField(blank=True, allow_unicode=True)


class RelatedPrepopulated(models.Model):
    parent = models.ForeignKey(MainPrepopulated, models.CASCADE)
    name = models.CharField(max_length=75)
    fk = models.ForeignKey('self', models.CASCADE, blank=True, null=True)
    m2m = models.ManyToManyField('self', blank=True)
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


class UnchangeableObject(models.Model):
    """
    Model whose change_view is disabled in admin
    Refs #20640.
    """


class UserMessenger(models.Model):
    """
    Dummy class for testing message_user functions on ModelAdmin
    """


class Simple(models.Model):
    """
    Simple model with nothing on it for use in testing
    """


class Choice(models.Model):
    choice = models.IntegerField(
        blank=True, null=True,
        choices=((1, 'Yes'), (0, 'No'), (None, 'No opinion')),
    )


class ParentWithDependentChildren(models.Model):
    """
    Issue #20522
    Model where the validation of child foreign-key relationships depends
    on validation of the parent
    """
    some_required_info = models.PositiveIntegerField()
    family_name = models.CharField(max_length=255, blank=False)


class DependentChild(models.Model):
    """
    Issue #20522
    Model that depends on validation of the parent class for one of its
    fields to validate during clean
    """
    parent = models.ForeignKey(ParentWithDependentChildren, models.CASCADE)
    family_name = models.CharField(max_length=255)


class _Manager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(pk__gt=1)


class FilteredManager(models.Model):
    def __str__(self):
        return "PK=%d" % self.pk

    pk_gt_1 = _Manager()
    objects = models.Manager()


class EmptyModelVisible(models.Model):
    """ See ticket #11277. """


class EmptyModelHidden(models.Model):
    """ See ticket #11277. """


class EmptyModelMixin(models.Model):
    """ See ticket #11277. """


class State(models.Model):
    name = models.CharField(max_length=100, verbose_name='State verbose_name')


class City(models.Model):
    state = models.ForeignKey(State, models.CASCADE)
    name = models.CharField(max_length=100, verbose_name='City verbose_name')

    def get_absolute_url(self):
        return '/dummy/%s/' % self.pk


class Restaurant(models.Model):
    city = models.ForeignKey(City, models.CASCADE)
    name = models.CharField(max_length=100)

    def get_absolute_url(self):
        return '/dummy/%s/' % self.pk


class Worker(models.Model):
    work_at = models.ForeignKey(Restaurant, models.CASCADE)
    name = models.CharField(max_length=50)
    surname = models.CharField(max_length=50)


# Models for #23329
class ReferencedByParent(models.Model):
    name = models.CharField(max_length=20, unique=True)


class ParentWithFK(models.Model):
    fk = models.ForeignKey(
        ReferencedByParent,
        models.CASCADE,
        to_field='name',
        related_name='hidden+',
    )


class ChildOfReferer(ParentWithFK):
    pass


# Models for #23431
class InlineReferer(models.Model):
    pass


class ReferencedByInline(models.Model):
    name = models.CharField(max_length=20, unique=True)


class InlineReference(models.Model):
    referer = models.ForeignKey(InlineReferer, models.CASCADE)
    fk = models.ForeignKey(
        ReferencedByInline,
        models.CASCADE,
        to_field='name',
        related_name='hidden+',
    )


class Recipe(models.Model):
    rname = models.CharField(max_length=20, unique=True)


class Ingredient(models.Model):
    iname = models.CharField(max_length=20, unique=True)
    recipes = models.ManyToManyField(Recipe, through='RecipeIngredient')


class RecipeIngredient(models.Model):
    ingredient = models.ForeignKey(Ingredient, models.CASCADE, to_field='iname')
    recipe = models.ForeignKey(Recipe, models.CASCADE, to_field='rname')


# Model for #23839
class NotReferenced(models.Model):
    # Don't point any FK at this model.
    pass


# Models for #23934
class ExplicitlyProvidedPK(models.Model):
    name = models.IntegerField(primary_key=True)


class ImplicitlyGeneratedPK(models.Model):
    name = models.IntegerField(unique=True)


# Models for #25622
class ReferencedByGenRel(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')


class GenRelReference(models.Model):
    references = GenericRelation(ReferencedByGenRel)


class ParentWithUUIDPK(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)

    def __str__(self):
        return str(self.id)


class RelatedWithUUIDPKModel(models.Model):
    parent = models.ForeignKey(ParentWithUUIDPK, on_delete=models.SET_NULL, null=True, blank=True)


class Author(models.Model):
    pass


class Authorship(models.Model):
    book = models.ForeignKey(Book, models.CASCADE)
    author = models.ForeignKey(Author, models.CASCADE)


class UserProxy(User):
    """Proxy a model with a different app_label."""
    class Meta:
        proxy = True


class ReadOnlyRelatedField(models.Model):
    chapter = models.ForeignKey(Chapter, models.CASCADE)
    language = models.ForeignKey(Language, models.CASCADE)
    user = models.ForeignKey(User, models.CASCADE)

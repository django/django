import datetime
from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name

class BetterAuthor(Author):
    write_speed = models.IntegerField()

class Book(models.Model):
    author = models.ForeignKey(Author)
    title = models.CharField(max_length=100)

    class Meta:
        unique_together = (
            ('author', 'title'),
        )
        ordering = ['id']

    def __unicode__(self):
        return self.title

class BookWithCustomPK(models.Model):
    my_pk = models.DecimalField(max_digits=5, decimal_places=0, primary_key=True)
    author = models.ForeignKey(Author)
    title = models.CharField(max_length=100)

    def __unicode__(self):
        return u'%s: %s' % (self.my_pk, self.title)

class Editor(models.Model):
    name = models.CharField(max_length=100)

class BookWithOptionalAltEditor(models.Model):
    author = models.ForeignKey(Author)
    # Optional secondary author
    alt_editor = models.ForeignKey(Editor, blank=True, null=True)
    title = models.CharField(max_length=100)

    class Meta:
        unique_together = (
            ('author', 'title', 'alt_editor'),
        )

    def __unicode__(self):
        return self.title

class AlternateBook(Book):
    notes = models.CharField(max_length=100)

    def __unicode__(self):
        return u'%s - %s' % (self.title, self.notes)

class AuthorMeeting(models.Model):
    name = models.CharField(max_length=100)
    authors = models.ManyToManyField(Author)
    created = models.DateField(editable=False)

    def __unicode__(self):
        return self.name

class CustomPrimaryKey(models.Model):
    my_pk = models.CharField(max_length=10, primary_key=True)
    some_field = models.CharField(max_length=100)


# models for inheritance tests.

class Place(models.Model):
    name = models.CharField(max_length=50)
    city = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

class Owner(models.Model):
    auto_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    place = models.ForeignKey(Place)

    def __unicode__(self):
        return "%s at %s" % (self.name, self.place)

class Location(models.Model):
    place = models.ForeignKey(Place, unique=True)
    # this is purely for testing the data doesn't matter here :)
    lat = models.CharField(max_length=100)
    lon = models.CharField(max_length=100)

class OwnerProfile(models.Model):
    owner = models.OneToOneField(Owner, primary_key=True)
    age = models.PositiveIntegerField()

    def __unicode__(self):
        return "%s is %d" % (self.owner.name, self.age)

class Restaurant(Place):
    serves_pizza = models.BooleanField()

    def __unicode__(self):
        return self.name

class Product(models.Model):
    slug = models.SlugField(unique=True)

    def __unicode__(self):
        return self.slug

class Price(models.Model):
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __unicode__(self):
        return u"%s for %s" % (self.quantity, self.price)

    class Meta:
        unique_together = (('price', 'quantity'),)

class MexicanRestaurant(Restaurant):
    serves_tacos = models.BooleanField()

class ClassyMexicanRestaurant(MexicanRestaurant):
    restaurant = models.OneToOneField(MexicanRestaurant, parent_link=True, primary_key=True)
    tacos_are_yummy = models.BooleanField()

# models for testing unique_together validation when a fk is involved and
# using inlineformset_factory.
class Repository(models.Model):
    name = models.CharField(max_length=25)

    def __unicode__(self):
        return self.name

class Revision(models.Model):
    repository = models.ForeignKey(Repository)
    revision = models.CharField(max_length=40)

    class Meta:
        unique_together = (("repository", "revision"),)

    def __unicode__(self):
        return u"%s (%s)" % (self.revision, unicode(self.repository))

# models for testing callable defaults (see bug #7975). If you define a model
# with a callable default value, you cannot rely on the initial value in a
# form.
class Person(models.Model):
    name = models.CharField(max_length=128)

class Membership(models.Model):
    person = models.ForeignKey(Person)
    date_joined = models.DateTimeField(default=datetime.datetime.now)
    karma = models.IntegerField()

# models for testing a null=True fk to a parent
class Team(models.Model):
    name = models.CharField(max_length=100)

class Player(models.Model):
    team = models.ForeignKey(Team, null=True)
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

# Models for testing custom ModelForm save methods in formsets and inline formsets
class Poet(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class Poem(models.Model):
    poet = models.ForeignKey(Poet)
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class Post(models.Model):
    title = models.CharField(max_length=50, unique_for_date='posted', blank=True)
    slug = models.CharField(max_length=50, unique_for_year='posted', blank=True)
    subtitle = models.CharField(max_length=50, unique_for_month='posted', blank=True)
    posted = models.DateField()

    def __unicode__(self):
        return self.name

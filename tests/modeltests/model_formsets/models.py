import datetime
from django import forms
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

__test__ = {'API_TESTS': """

>>> from datetime import date

>>> from django.forms.models import modelformset_factory

>>> qs = Author.objects.all()
>>> AuthorFormSet = modelformset_factory(Author, extra=3)

>>> formset = AuthorFormSet(queryset=qs)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_form-0-name">Name:</label> <input id="id_form-0-name" type="text" name="form-0-name" maxlength="100" /><input type="hidden" name="form-0-id" id="id_form-0-id" /></p>
<p><label for="id_form-1-name">Name:</label> <input id="id_form-1-name" type="text" name="form-1-name" maxlength="100" /><input type="hidden" name="form-1-id" id="id_form-1-id" /></p>
<p><label for="id_form-2-name">Name:</label> <input id="id_form-2-name" type="text" name="form-2-name" maxlength="100" /><input type="hidden" name="form-2-id" id="id_form-2-id" /></p>

>>> data = {
...     'form-TOTAL_FORMS': '3', # the number of forms rendered
...     'form-INITIAL_FORMS': '0', # the number of forms with initial data
...     'form-MAX_NUM_FORMS': '', # the max number of forms
...     'form-0-name': 'Charles Baudelaire',
...     'form-1-name': 'Arthur Rimbaud',
...     'form-2-name': '',
... }

>>> formset = AuthorFormSet(data=data, queryset=qs)
>>> formset.is_valid()
True

>>> formset.save()
[<Author: Charles Baudelaire>, <Author: Arthur Rimbaud>]

>>> for author in Author.objects.order_by('name'):
...     print author.name
Arthur Rimbaud
Charles Baudelaire


Gah! We forgot Paul Verlaine. Let's create a formset to edit the existing
authors with an extra form to add him. We *could* pass in a queryset to
restrict the Author objects we edit, but in this case we'll use it to display
them in alphabetical order by name.

>>> qs = Author.objects.order_by('name')
>>> AuthorFormSet = modelformset_factory(Author, extra=1, can_delete=False)

>>> formset = AuthorFormSet(queryset=qs)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_form-0-name">Name:</label> <input id="id_form-0-name" type="text" name="form-0-name" value="Arthur Rimbaud" maxlength="100" /><input type="hidden" name="form-0-id" value="2" id="id_form-0-id" /></p>
<p><label for="id_form-1-name">Name:</label> <input id="id_form-1-name" type="text" name="form-1-name" value="Charles Baudelaire" maxlength="100" /><input type="hidden" name="form-1-id" value="1" id="id_form-1-id" /></p>
<p><label for="id_form-2-name">Name:</label> <input id="id_form-2-name" type="text" name="form-2-name" maxlength="100" /><input type="hidden" name="form-2-id" id="id_form-2-id" /></p>


>>> data = {
...     'form-TOTAL_FORMS': '3', # the number of forms rendered
...     'form-INITIAL_FORMS': '2', # the number of forms with initial data
...     'form-MAX_NUM_FORMS': '', # the max number of forms
...     'form-0-id': '2',
...     'form-0-name': 'Arthur Rimbaud',
...     'form-1-id': '1',
...     'form-1-name': 'Charles Baudelaire',
...     'form-2-name': 'Paul Verlaine',
... }

>>> formset = AuthorFormSet(data=data, queryset=qs)
>>> formset.is_valid()
True

# Only changed or new objects are returned from formset.save()
>>> formset.save()
[<Author: Paul Verlaine>]

>>> for author in Author.objects.order_by('name'):
...     print author.name
Arthur Rimbaud
Charles Baudelaire
Paul Verlaine


This probably shouldn't happen, but it will. If an add form was marked for
deltetion, make sure we don't save that form.

>>> qs = Author.objects.order_by('name')
>>> AuthorFormSet = modelformset_factory(Author, extra=1, can_delete=True)

>>> formset = AuthorFormSet(queryset=qs)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_form-0-name">Name:</label> <input id="id_form-0-name" type="text" name="form-0-name" value="Arthur Rimbaud" maxlength="100" /></p>
<p><label for="id_form-0-DELETE">Delete:</label> <input type="checkbox" name="form-0-DELETE" id="id_form-0-DELETE" /><input type="hidden" name="form-0-id" value="2" id="id_form-0-id" /></p>
<p><label for="id_form-1-name">Name:</label> <input id="id_form-1-name" type="text" name="form-1-name" value="Charles Baudelaire" maxlength="100" /></p>
<p><label for="id_form-1-DELETE">Delete:</label> <input type="checkbox" name="form-1-DELETE" id="id_form-1-DELETE" /><input type="hidden" name="form-1-id" value="1" id="id_form-1-id" /></p>
<p><label for="id_form-2-name">Name:</label> <input id="id_form-2-name" type="text" name="form-2-name" value="Paul Verlaine" maxlength="100" /></p>
<p><label for="id_form-2-DELETE">Delete:</label> <input type="checkbox" name="form-2-DELETE" id="id_form-2-DELETE" /><input type="hidden" name="form-2-id" value="3" id="id_form-2-id" /></p>
<p><label for="id_form-3-name">Name:</label> <input id="id_form-3-name" type="text" name="form-3-name" maxlength="100" /></p>
<p><label for="id_form-3-DELETE">Delete:</label> <input type="checkbox" name="form-3-DELETE" id="id_form-3-DELETE" /><input type="hidden" name="form-3-id" id="id_form-3-id" /></p>

>>> data = {
...     'form-TOTAL_FORMS': '4', # the number of forms rendered
...     'form-INITIAL_FORMS': '3', # the number of forms with initial data
...     'form-MAX_NUM_FORMS': '', # the max number of forms
...     'form-0-id': '2',
...     'form-0-name': 'Arthur Rimbaud',
...     'form-1-id': '1',
...     'form-1-name': 'Charles Baudelaire',
...     'form-2-id': '3',
...     'form-2-name': 'Paul Verlaine',
...     'form-3-name': 'Walt Whitman',
...     'form-3-DELETE': 'on',
... }

>>> formset = AuthorFormSet(data=data, queryset=qs)
>>> formset.is_valid()
True

# No objects were changed or saved so nothing will come back.
>>> formset.save()
[]

>>> for author in Author.objects.order_by('name'):
...     print author.name
Arthur Rimbaud
Charles Baudelaire
Paul Verlaine

Let's edit a record to ensure save only returns that one record.

>>> data = {
...     'form-TOTAL_FORMS': '4', # the number of forms rendered
...     'form-INITIAL_FORMS': '3', # the number of forms with initial data
...     'form-MAX_NUM_FORMS': '', # the max number of forms
...     'form-0-id': '2',
...     'form-0-name': 'Walt Whitman',
...     'form-1-id': '1',
...     'form-1-name': 'Charles Baudelaire',
...     'form-2-id': '3',
...     'form-2-name': 'Paul Verlaine',
...     'form-3-name': '',
...     'form-3-DELETE': '',
... }

>>> formset = AuthorFormSet(data=data, queryset=qs)
>>> formset.is_valid()
True

# One record has changed.
>>> formset.save()
[<Author: Walt Whitman>]

Test the behavior of commit=False and save_m2m

>>> meeting = AuthorMeeting.objects.create(created=date.today())
>>> meeting.authors = Author.objects.all()

# create an Author instance to add to the meeting.
>>> new_author = Author.objects.create(name=u'John Steinbeck')

>>> AuthorMeetingFormSet = modelformset_factory(AuthorMeeting, extra=1, can_delete=True)
>>> data = {
...     'form-TOTAL_FORMS': '2', # the number of forms rendered
...     'form-INITIAL_FORMS': '1', # the number of forms with initial data
...     'form-MAX_NUM_FORMS': '', # the max number of forms
...     'form-0-id': '1',
...     'form-0-name': '2nd Tuesday of the Week Meeting',
...     'form-0-authors': [2, 1, 3, 4],
...     'form-1-name': '',
...     'form-1-authors': '',
...     'form-1-DELETE': '',
... }
>>> formset = AuthorMeetingFormSet(data=data, queryset=AuthorMeeting.objects.all())
>>> formset.is_valid()
True
>>> instances = formset.save(commit=False)
>>> for instance in instances:
...     instance.created = date.today()
...     instance.save()
>>> formset.save_m2m()
>>> instances[0].authors.all()
[<Author: Charles Baudelaire>, <Author: John Steinbeck>, <Author: Paul Verlaine>, <Author: Walt Whitman>]

# delete the author we created to allow later tests to continue working.
>>> new_author.delete()

Test the behavior of max_num with model formsets. It should allow all existing
related objects/inlines for a given object to be displayed, but not allow
the creation of new inlines beyond max_num.

>>> qs = Author.objects.order_by('name')

>>> AuthorFormSet = modelformset_factory(Author, max_num=None, extra=3)
>>> formset = AuthorFormSet(queryset=qs)
>>> len(formset.forms)
6
>>> len(formset.extra_forms)
3

>>> AuthorFormSet = modelformset_factory(Author, max_num=4, extra=3)
>>> formset = AuthorFormSet(queryset=qs)
>>> len(formset.forms)
4
>>> len(formset.extra_forms)
1

>>> AuthorFormSet = modelformset_factory(Author, max_num=0, extra=3)
>>> formset = AuthorFormSet(queryset=qs)
>>> len(formset.forms)
3
>>> len(formset.extra_forms)
0

>>> AuthorFormSet = modelformset_factory(Author, max_num=None)
>>> formset = AuthorFormSet(queryset=qs)
>>> [x.name for x in formset.get_queryset()]
[u'Charles Baudelaire', u'Paul Verlaine', u'Walt Whitman']

>>> AuthorFormSet = modelformset_factory(Author, max_num=0)
>>> formset = AuthorFormSet(queryset=qs)
>>> [x.name for x in formset.get_queryset()]
[u'Charles Baudelaire', u'Paul Verlaine', u'Walt Whitman']

>>> AuthorFormSet = modelformset_factory(Author, max_num=4)
>>> formset = AuthorFormSet(queryset=qs)
>>> [x.name for x in formset.get_queryset()]
[u'Charles Baudelaire', u'Paul Verlaine', u'Walt Whitman']


# ModelForm with a custom save method in a formset ###########################

>>> class PoetForm(forms.ModelForm):
...     def save(self, commit=True):
...         # change the name to "Vladimir Mayakovsky" just to be a jerk.
...         author = super(PoetForm, self).save(commit=False)
...         author.name = u"Vladimir Mayakovsky"
...         if commit:
...             author.save()
...         return author

>>> PoetFormSet = modelformset_factory(Poet, form=PoetForm)

>>> data = {
...     'form-TOTAL_FORMS': '3', # the number of forms rendered
...     'form-INITIAL_FORMS': '0', # the number of forms with initial data
...     'form-MAX_NUM_FORMS': '', # the max number of forms
...     'form-0-name': 'Walt Whitman',
...     'form-1-name': 'Charles Baudelaire',
...     'form-2-name': '',
... }

>>> qs = Poet.objects.all()
>>> formset = PoetFormSet(data=data, queryset=qs)
>>> formset.is_valid()
True

>>> formset.save()
[<Poet: Vladimir Mayakovsky>, <Poet: Vladimir Mayakovsky>]


# Model inheritance in model formsets ########################################

>>> BetterAuthorFormSet = modelformset_factory(BetterAuthor)
>>> formset = BetterAuthorFormSet()
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_form-0-name">Name:</label> <input id="id_form-0-name" type="text" name="form-0-name" maxlength="100" /></p>
<p><label for="id_form-0-write_speed">Write speed:</label> <input type="text" name="form-0-write_speed" id="id_form-0-write_speed" /><input type="hidden" name="form-0-author_ptr" id="id_form-0-author_ptr" /></p>

>>> data = {
...     'form-TOTAL_FORMS': '1', # the number of forms rendered
...     'form-INITIAL_FORMS': '0', # the number of forms with initial data
...     'form-MAX_NUM_FORMS': '', # the max number of forms
...     'form-0-author_ptr': '',
...     'form-0-name': 'Ernest Hemingway',
...     'form-0-write_speed': '10',
... }

>>> formset = BetterAuthorFormSet(data)
>>> formset.is_valid()
True
>>> formset.save()
[<BetterAuthor: Ernest Hemingway>]
>>> hemingway_id = BetterAuthor.objects.get(name="Ernest Hemingway").pk

>>> formset = BetterAuthorFormSet()
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_form-0-name">Name:</label> <input id="id_form-0-name" type="text" name="form-0-name" value="Ernest Hemingway" maxlength="100" /></p>
<p><label for="id_form-0-write_speed">Write speed:</label> <input type="text" name="form-0-write_speed" value="10" id="id_form-0-write_speed" /><input type="hidden" name="form-0-author_ptr" value="..." id="id_form-0-author_ptr" /></p>
<p><label for="id_form-1-name">Name:</label> <input id="id_form-1-name" type="text" name="form-1-name" maxlength="100" /></p>
<p><label for="id_form-1-write_speed">Write speed:</label> <input type="text" name="form-1-write_speed" id="id_form-1-write_speed" /><input type="hidden" name="form-1-author_ptr" id="id_form-1-author_ptr" /></p>

>>> data = {
...     'form-TOTAL_FORMS': '2', # the number of forms rendered
...     'form-INITIAL_FORMS': '1', # the number of forms with initial data
...     'form-MAX_NUM_FORMS': '', # the max number of forms
...     'form-0-author_ptr': hemingway_id,
...     'form-0-name': 'Ernest Hemingway',
...     'form-0-write_speed': '10',
...     'form-1-author_ptr': '',
...     'form-1-name': '',
...     'form-1-write_speed': '',
... }

>>> formset = BetterAuthorFormSet(data)
>>> formset.is_valid()
True
>>> formset.save()
[]

# Inline Formsets ############################################################

We can also create a formset that is tied to a parent model. This is how the
admin system's edit inline functionality works.

>>> from django.forms.models import inlineformset_factory

>>> AuthorBooksFormSet = inlineformset_factory(Author, Book, can_delete=False, extra=3)
>>> author = Author.objects.get(name='Charles Baudelaire')

>>> formset = AuthorBooksFormSet(instance=author)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_book_set-0-title">Title:</label> <input id="id_book_set-0-title" type="text" name="book_set-0-title" maxlength="100" /><input type="hidden" name="book_set-0-author" value="1" id="id_book_set-0-author" /><input type="hidden" name="book_set-0-id" id="id_book_set-0-id" /></p>
<p><label for="id_book_set-1-title">Title:</label> <input id="id_book_set-1-title" type="text" name="book_set-1-title" maxlength="100" /><input type="hidden" name="book_set-1-author" value="1" id="id_book_set-1-author" /><input type="hidden" name="book_set-1-id" id="id_book_set-1-id" /></p>
<p><label for="id_book_set-2-title">Title:</label> <input id="id_book_set-2-title" type="text" name="book_set-2-title" maxlength="100" /><input type="hidden" name="book_set-2-author" value="1" id="id_book_set-2-author" /><input type="hidden" name="book_set-2-id" id="id_book_set-2-id" /></p>

>>> data = {
...     'book_set-TOTAL_FORMS': '3', # the number of forms rendered
...     'book_set-INITIAL_FORMS': '0', # the number of forms with initial data
...     'book_set-MAX_NUM_FORMS': '', # the max number of forms
...     'book_set-0-title': 'Les Fleurs du Mal',
...     'book_set-1-title': '',
...     'book_set-2-title': '',
... }

>>> formset = AuthorBooksFormSet(data, instance=author)
>>> formset.is_valid()
True

>>> formset.save()
[<Book: Les Fleurs du Mal>]

>>> for book in author.book_set.all():
...     print book.title
Les Fleurs du Mal


Now that we've added a book to Charles Baudelaire, let's try adding another
one. This time though, an edit form will be available for every existing
book.

>>> AuthorBooksFormSet = inlineformset_factory(Author, Book, can_delete=False, extra=2)
>>> author = Author.objects.get(name='Charles Baudelaire')

>>> formset = AuthorBooksFormSet(instance=author)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_book_set-0-title">Title:</label> <input id="id_book_set-0-title" type="text" name="book_set-0-title" value="Les Fleurs du Mal" maxlength="100" /><input type="hidden" name="book_set-0-author" value="1" id="id_book_set-0-author" /><input type="hidden" name="book_set-0-id" value="1" id="id_book_set-0-id" /></p>
<p><label for="id_book_set-1-title">Title:</label> <input id="id_book_set-1-title" type="text" name="book_set-1-title" maxlength="100" /><input type="hidden" name="book_set-1-author" value="1" id="id_book_set-1-author" /><input type="hidden" name="book_set-1-id" id="id_book_set-1-id" /></p>
<p><label for="id_book_set-2-title">Title:</label> <input id="id_book_set-2-title" type="text" name="book_set-2-title" maxlength="100" /><input type="hidden" name="book_set-2-author" value="1" id="id_book_set-2-author" /><input type="hidden" name="book_set-2-id" id="id_book_set-2-id" /></p>

>>> data = {
...     'book_set-TOTAL_FORMS': '3', # the number of forms rendered
...     'book_set-INITIAL_FORMS': '1', # the number of forms with initial data
...     'book_set-MAX_NUM_FORMS': '', # the max number of forms
...     'book_set-0-id': '1',
...     'book_set-0-title': 'Les Fleurs du Mal',
...     'book_set-1-title': 'Les Paradis Artificiels',
...     'book_set-2-title': '',
... }

>>> formset = AuthorBooksFormSet(data, instance=author)
>>> formset.is_valid()
True

>>> formset.save()
[<Book: Les Paradis Artificiels>]

As you can see, 'Les Paradis Artificiels' is now a book belonging to Charles Baudelaire.

>>> for book in author.book_set.order_by('id'):
...     print book.title
Les Fleurs du Mal
Les Paradis Artificiels

The save_as_new parameter lets you re-associate the data to a new instance.
This is used in the admin for save_as functionality.

>>> data = {
...     'book_set-TOTAL_FORMS': '3', # the number of forms rendered
...     'book_set-INITIAL_FORMS': '2', # the number of forms with initial data
...     'book_set-MAX_NUM_FORMS': '', # the max number of forms
...     'book_set-0-id': '1',
...     'book_set-0-title': 'Les Fleurs du Mal',
...     'book_set-1-id': '2',
...     'book_set-1-title': 'Les Paradis Artificiels',
...     'book_set-2-title': '',
... }

>>> formset = AuthorBooksFormSet(data, instance=Author(), save_as_new=True)
>>> formset.is_valid()
True

>>> new_author = Author.objects.create(name='Charles Baudelaire')
>>> formset = AuthorBooksFormSet(data, instance=new_author, save_as_new=True)
>>> [book for book in formset.save() if book.author.pk == new_author.pk]
[<Book: Les Fleurs du Mal>, <Book: Les Paradis Artificiels>]

Test using a custom prefix on an inline formset.

>>> formset = AuthorBooksFormSet(prefix="test")
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_test-0-title">Title:</label> <input id="id_test-0-title" type="text" name="test-0-title" maxlength="100" /><input type="hidden" name="test-0-author" id="id_test-0-author" /><input type="hidden" name="test-0-id" id="id_test-0-id" /></p>
<p><label for="id_test-1-title">Title:</label> <input id="id_test-1-title" type="text" name="test-1-title" maxlength="100" /><input type="hidden" name="test-1-author" id="id_test-1-author" /><input type="hidden" name="test-1-id" id="id_test-1-id" /></p>

Test inline formsets where the inline-edited object has a custom primary key that is not the fk to the parent object.

>>> AuthorBooksFormSet2 = inlineformset_factory(Author, BookWithCustomPK, can_delete=False, extra=1)

>>> formset = AuthorBooksFormSet2(instance=author)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_bookwithcustompk_set-0-my_pk">My pk:</label> <input type="text" name="bookwithcustompk_set-0-my_pk" id="id_bookwithcustompk_set-0-my_pk" /></p>
    <p><label for="id_bookwithcustompk_set-0-title">Title:</label> <input id="id_bookwithcustompk_set-0-title" type="text" name="bookwithcustompk_set-0-title" maxlength="100" /><input type="hidden" name="bookwithcustompk_set-0-author" value="1" id="id_bookwithcustompk_set-0-author" /></p>

>>> data = {
...     'bookwithcustompk_set-TOTAL_FORMS': '1', # the number of forms rendered
...     'bookwithcustompk_set-INITIAL_FORMS': '0', # the number of forms with initial data
...     'bookwithcustompk_set-MAX_NUM_FORMS': '', # the max number of forms
...     'bookwithcustompk_set-0-my_pk': '77777',
...     'bookwithcustompk_set-0-title': 'Les Fleurs du Mal',
... }

>>> formset = AuthorBooksFormSet2(data, instance=author)
>>> formset.is_valid()
True

>>> formset.save()
[<BookWithCustomPK: 77777: Les Fleurs du Mal>]

>>> for book in author.bookwithcustompk_set.all():
...     print book.title
Les Fleurs du Mal

Test inline formsets where the inline-edited object uses multi-table inheritance, thus
has a non AutoField yet auto-created primary key.

>>> AuthorBooksFormSet3 = inlineformset_factory(Author, AlternateBook, can_delete=False, extra=1)

>>> formset = AuthorBooksFormSet3(instance=author)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_alternatebook_set-0-title">Title:</label> <input id="id_alternatebook_set-0-title" type="text" name="alternatebook_set-0-title" maxlength="100" /></p>
    <p><label for="id_alternatebook_set-0-notes">Notes:</label> <input id="id_alternatebook_set-0-notes" type="text" name="alternatebook_set-0-notes" maxlength="100" /><input type="hidden" name="alternatebook_set-0-author" value="1" id="id_alternatebook_set-0-author" /><input type="hidden" name="alternatebook_set-0-book_ptr" id="id_alternatebook_set-0-book_ptr" /></p>


>>> data = {
...     'alternatebook_set-TOTAL_FORMS': '1', # the number of forms rendered
...     'alternatebook_set-INITIAL_FORMS': '0', # the number of forms with initial data
...     'alternatebook_set-MAX_NUM_FORMS': '', # the max number of forms
...     'alternatebook_set-0-title': 'Flowers of Evil',
...     'alternatebook_set-0-notes': 'English translation of Les Fleurs du Mal'
... }

>>> formset = AuthorBooksFormSet3(data, instance=author)
>>> formset.is_valid()
True

>>> formset.save()
[<AlternateBook: Flowers of Evil - English translation of Les Fleurs du Mal>]


# ModelForm with a custom save method in an inline formset ###################

>>> class PoemForm(forms.ModelForm):
...     def save(self, commit=True):
...         # change the name to "Brooklyn Bridge" just to be a jerk.
...         poem = super(PoemForm, self).save(commit=False)
...         poem.name = u"Brooklyn Bridge"
...         if commit:
...             poem.save()
...         return poem

>>> PoemFormSet = inlineformset_factory(Poet, Poem, form=PoemForm)

>>> data = {
...     'poem_set-TOTAL_FORMS': '3', # the number of forms rendered
...     'poem_set-INITIAL_FORMS': '0', # the number of forms with initial data
...     'poem_set-MAX_NUM_FORMS': '', # the max number of forms
...     'poem_set-0-name': 'The Cloud in Trousers',
...     'poem_set-1-name': 'I',
...     'poem_set-2-name': '',
... }

>>> poet = Poet.objects.create(name='Vladimir Mayakovsky')
>>> formset = PoemFormSet(data=data, instance=poet)
>>> formset.is_valid()
True

>>> formset.save()
[<Poem: Brooklyn Bridge>, <Poem: Brooklyn Bridge>]

We can provide a custom queryset to our InlineFormSet:

>>> custom_qs = Book.objects.order_by('-title')
>>> formset = AuthorBooksFormSet(instance=author, queryset=custom_qs)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_book_set-0-title">Title:</label> <input id="id_book_set-0-title" type="text" name="book_set-0-title" value="Les Paradis Artificiels" maxlength="100" /><input type="hidden" name="book_set-0-author" value="1" id="id_book_set-0-author" /><input type="hidden" name="book_set-0-id" value="2" id="id_book_set-0-id" /></p>
<p><label for="id_book_set-1-title">Title:</label> <input id="id_book_set-1-title" type="text" name="book_set-1-title" value="Les Fleurs du Mal" maxlength="100" /><input type="hidden" name="book_set-1-author" value="1" id="id_book_set-1-author" /><input type="hidden" name="book_set-1-id" value="1" id="id_book_set-1-id" /></p>
<p><label for="id_book_set-2-title">Title:</label> <input id="id_book_set-2-title" type="text" name="book_set-2-title" value="Flowers of Evil" maxlength="100" /><input type="hidden" name="book_set-2-author" value="1" id="id_book_set-2-author" /><input type="hidden" name="book_set-2-id" value="5" id="id_book_set-2-id" /></p>
<p><label for="id_book_set-3-title">Title:</label> <input id="id_book_set-3-title" type="text" name="book_set-3-title" maxlength="100" /><input type="hidden" name="book_set-3-author" value="1" id="id_book_set-3-author" /><input type="hidden" name="book_set-3-id" id="id_book_set-3-id" /></p>
<p><label for="id_book_set-4-title">Title:</label> <input id="id_book_set-4-title" type="text" name="book_set-4-title" maxlength="100" /><input type="hidden" name="book_set-4-author" value="1" id="id_book_set-4-author" /><input type="hidden" name="book_set-4-id" id="id_book_set-4-id" /></p>

>>> data = {
...     'book_set-TOTAL_FORMS': '5', # the number of forms rendered
...     'book_set-INITIAL_FORMS': '3', # the number of forms with initial data
...     'book_set-MAX_NUM_FORMS': '', # the max number of forms
...     'book_set-0-id': '1',
...     'book_set-0-title': 'Les Fleurs du Mal',
...     'book_set-1-id': '2',
...     'book_set-1-title': 'Les Paradis Artificiels',
...     'book_set-2-id': '5',
...     'book_set-2-title': 'Flowers of Evil',
...     'book_set-3-title': 'Revue des deux mondes',
...     'book_set-4-title': '',
... }
>>> formset = AuthorBooksFormSet(data, instance=author, queryset=custom_qs)
>>> formset.is_valid()
True

>>> custom_qs = Book.objects.filter(title__startswith='F')
>>> formset = AuthorBooksFormSet(instance=author, queryset=custom_qs)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_book_set-0-title">Title:</label> <input id="id_book_set-0-title" type="text" name="book_set-0-title" value="Flowers of Evil" maxlength="100" /><input type="hidden" name="book_set-0-author" value="1" id="id_book_set-0-author" /><input type="hidden" name="book_set-0-id" value="5" id="id_book_set-0-id" /></p>
<p><label for="id_book_set-1-title">Title:</label> <input id="id_book_set-1-title" type="text" name="book_set-1-title" maxlength="100" /><input type="hidden" name="book_set-1-author" value="1" id="id_book_set-1-author" /><input type="hidden" name="book_set-1-id" id="id_book_set-1-id" /></p>
<p><label for="id_book_set-2-title">Title:</label> <input id="id_book_set-2-title" type="text" name="book_set-2-title" maxlength="100" /><input type="hidden" name="book_set-2-author" value="1" id="id_book_set-2-author" /><input type="hidden" name="book_set-2-id" id="id_book_set-2-id" /></p>
>>> data = {
...     'book_set-TOTAL_FORMS': '3', # the number of forms rendered
...     'book_set-INITIAL_FORMS': '1', # the number of forms with initial data
...     'book_set-MAX_NUM_FORMS': '', # the max number of forms
...     'book_set-0-id': '5',
...     'book_set-0-title': 'Flowers of Evil',
...     'book_set-1-title': 'Revue des deux mondes',
...     'book_set-2-title': '',
... }
>>> formset = AuthorBooksFormSet(data, instance=author, queryset=custom_qs)
>>> formset.is_valid()
True


# Test a custom primary key ###################################################

We need to ensure that it is displayed

>>> CustomPrimaryKeyFormSet = modelformset_factory(CustomPrimaryKey)
>>> formset = CustomPrimaryKeyFormSet()
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_form-0-my_pk">My pk:</label> <input id="id_form-0-my_pk" type="text" name="form-0-my_pk" maxlength="10" /></p>
<p><label for="id_form-0-some_field">Some field:</label> <input id="id_form-0-some_field" type="text" name="form-0-some_field" maxlength="100" /></p>

# Custom primary keys with ForeignKey, OneToOneField and AutoField ############

>>> place = Place(name=u'Giordanos', city=u'Chicago')
>>> place.save()

>>> FormSet = inlineformset_factory(Place, Owner, extra=2, can_delete=False)
>>> formset = FormSet(instance=place)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_owner_set-0-name">Name:</label> <input id="id_owner_set-0-name" type="text" name="owner_set-0-name" maxlength="100" /><input type="hidden" name="owner_set-0-place" value="1" id="id_owner_set-0-place" /><input type="hidden" name="owner_set-0-auto_id" id="id_owner_set-0-auto_id" /></p>
<p><label for="id_owner_set-1-name">Name:</label> <input id="id_owner_set-1-name" type="text" name="owner_set-1-name" maxlength="100" /><input type="hidden" name="owner_set-1-place" value="1" id="id_owner_set-1-place" /><input type="hidden" name="owner_set-1-auto_id" id="id_owner_set-1-auto_id" /></p>

>>> data = {
...     'owner_set-TOTAL_FORMS': '2',
...     'owner_set-INITIAL_FORMS': '0',
...     'owner_set-MAX_NUM_FORMS': '',
...     'owner_set-0-auto_id': '',
...     'owner_set-0-name': u'Joe Perry',
...     'owner_set-1-auto_id': '',
...     'owner_set-1-name': '',
... }
>>> formset = FormSet(data, instance=place)
>>> formset.is_valid()
True
>>> formset.save()
[<Owner: Joe Perry at Giordanos>]

>>> formset = FormSet(instance=place)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_owner_set-0-name">Name:</label> <input id="id_owner_set-0-name" type="text" name="owner_set-0-name" value="Joe Perry" maxlength="100" /><input type="hidden" name="owner_set-0-place" value="1" id="id_owner_set-0-place" /><input type="hidden" name="owner_set-0-auto_id" value="1" id="id_owner_set-0-auto_id" /></p>
<p><label for="id_owner_set-1-name">Name:</label> <input id="id_owner_set-1-name" type="text" name="owner_set-1-name" maxlength="100" /><input type="hidden" name="owner_set-1-place" value="1" id="id_owner_set-1-place" /><input type="hidden" name="owner_set-1-auto_id" id="id_owner_set-1-auto_id" /></p>
<p><label for="id_owner_set-2-name">Name:</label> <input id="id_owner_set-2-name" type="text" name="owner_set-2-name" maxlength="100" /><input type="hidden" name="owner_set-2-place" value="1" id="id_owner_set-2-place" /><input type="hidden" name="owner_set-2-auto_id" id="id_owner_set-2-auto_id" /></p>

>>> data = {
...     'owner_set-TOTAL_FORMS': '3',
...     'owner_set-INITIAL_FORMS': '1',
...     'owner_set-MAX_NUM_FORMS': '',
...     'owner_set-0-auto_id': u'1',
...     'owner_set-0-name': u'Joe Perry',
...     'owner_set-1-auto_id': '',
...     'owner_set-1-name': u'Jack Berry',
...     'owner_set-2-auto_id': '',
...     'owner_set-2-name': '',
... }
>>> formset = FormSet(data, instance=place)
>>> formset.is_valid()
True
>>> formset.save()
[<Owner: Jack Berry at Giordanos>]

# Ensure a custom primary key that is a ForeignKey or OneToOneField get rendered for the user to choose.

>>> FormSet = modelformset_factory(OwnerProfile)
>>> formset = FormSet()
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_form-0-owner">Owner:</label> <select name="form-0-owner" id="id_form-0-owner">
<option value="" selected="selected">---------</option>
<option value="1">Joe Perry at Giordanos</option>
<option value="2">Jack Berry at Giordanos</option>
</select></p>
<p><label for="id_form-0-age">Age:</label> <input type="text" name="form-0-age" id="id_form-0-age" /></p>

>>> owner = Owner.objects.get(name=u'Joe Perry')
>>> FormSet = inlineformset_factory(Owner, OwnerProfile, max_num=1, can_delete=False)
>>> FormSet.max_num
1
>>> formset = FormSet(instance=owner)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_ownerprofile-0-age">Age:</label> <input type="text" name="ownerprofile-0-age" id="id_ownerprofile-0-age" /><input type="hidden" name="ownerprofile-0-owner" value="1" id="id_ownerprofile-0-owner" /></p>

>>> data = {
...     'ownerprofile-TOTAL_FORMS': '1',
...     'ownerprofile-INITIAL_FORMS': '0',
...     'ownerprofile-MAX_NUM_FORMS': '1',
...     'ownerprofile-0-owner': '',
...     'ownerprofile-0-age': u'54',
... }
>>> formset = FormSet(data, instance=owner)
>>> formset.is_valid()
True
>>> formset.save()
[<OwnerProfile: Joe Perry is 54>]
>>> formset = FormSet(instance=owner)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_ownerprofile-0-age">Age:</label> <input type="text" name="ownerprofile-0-age" value="54" id="id_ownerprofile-0-age" /><input type="hidden" name="ownerprofile-0-owner" value="1" id="id_ownerprofile-0-owner" /></p>

>>> data = {
...     'ownerprofile-TOTAL_FORMS': '1',
...     'ownerprofile-INITIAL_FORMS': '1',
...     'ownerprofile-MAX_NUM_FORMS': '1',
...     'ownerprofile-0-owner': u'1',
...     'ownerprofile-0-age': u'55',
... }
>>> formset = FormSet(data, instance=owner)
>>> formset.is_valid()
True
>>> formset.save()
[<OwnerProfile: Joe Perry is 55>]

# ForeignKey with unique=True should enforce max_num=1

>>> FormSet = inlineformset_factory(Place, Location, can_delete=False)
>>> FormSet.max_num
1
>>> formset = FormSet(instance=place)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_location_set-0-lat">Lat:</label> <input id="id_location_set-0-lat" type="text" name="location_set-0-lat" maxlength="100" /></p>
<p><label for="id_location_set-0-lon">Lon:</label> <input id="id_location_set-0-lon" type="text" name="location_set-0-lon" maxlength="100" /><input type="hidden" name="location_set-0-place" value="1" id="id_location_set-0-place" /><input type="hidden" name="location_set-0-id" id="id_location_set-0-id" /></p>

# Foreign keys in parents ########################################

>>> from django.forms.models import _get_foreign_key

>>> type(_get_foreign_key(Restaurant, Owner))
<class 'django.db.models.fields.related.ForeignKey'>
>>> type(_get_foreign_key(MexicanRestaurant, Owner))
<class 'django.db.models.fields.related.ForeignKey'>

# unique/unique_together validation ###########################################

>>> FormSet = modelformset_factory(Product, extra=1)
>>> data = {
...     'form-TOTAL_FORMS': '1',
...     'form-INITIAL_FORMS': '0',
...     'form-MAX_NUM_FORMS': '',
...     'form-0-slug': 'car-red',
... }
>>> formset = FormSet(data)
>>> formset.is_valid()
True
>>> formset.save()
[<Product: car-red>]

>>> data = {
...     'form-TOTAL_FORMS': '1',
...     'form-INITIAL_FORMS': '0',
...     'form-MAX_NUM_FORMS': '',
...     'form-0-slug': 'car-red',
... }
>>> formset = FormSet(data)
>>> formset.is_valid()
False
>>> formset.errors
[{'slug': [u'Product with this Slug already exists.']}]

# unique_together

>>> FormSet = modelformset_factory(Price, extra=1)
>>> data = {
...     'form-TOTAL_FORMS': '1',
...     'form-INITIAL_FORMS': '0',
...     'form-MAX_NUM_FORMS': '',
...     'form-0-price': u'12.00',
...     'form-0-quantity': '1',
... }
>>> formset = FormSet(data)
>>> formset.is_valid()
True
>>> formset.save()
[<Price: 1 for 12.00>]

>>> data = {
...     'form-TOTAL_FORMS': '1',
...     'form-INITIAL_FORMS': '0',
...     'form-MAX_NUM_FORMS': '',
...     'form-0-price': u'12.00',
...     'form-0-quantity': '1',
... }
>>> formset = FormSet(data)
>>> formset.is_valid()
False
>>> formset.errors
[{'__all__': [u'Price with this Price and Quantity already exists.']}]

# unique_together with inlineformset_factory
# Also see bug #8882.

>>> repository = Repository.objects.create(name=u'Test Repo')
>>> FormSet = inlineformset_factory(Repository, Revision, extra=1)
>>> data = {
...     'revision_set-TOTAL_FORMS': '1',
...     'revision_set-INITIAL_FORMS': '0',
...     'revision_set-MAX_NUM_FORMS': '',
...     'revision_set-0-repository': repository.pk,
...     'revision_set-0-revision': '146239817507f148d448db38840db7c3cbf47c76',
...     'revision_set-0-DELETE': '',
... }
>>> formset = FormSet(data, instance=repository)
>>> formset.is_valid()
True
>>> formset.save()
[<Revision: 146239817507f148d448db38840db7c3cbf47c76 (Test Repo)>]

# attempt to save the same revision against against the same repo.
>>> data = {
...     'revision_set-TOTAL_FORMS': '1',
...     'revision_set-INITIAL_FORMS': '0',
...     'revision_set-MAX_NUM_FORMS': '',
...     'revision_set-0-repository': repository.pk,
...     'revision_set-0-revision': '146239817507f148d448db38840db7c3cbf47c76',
...     'revision_set-0-DELETE': '',
... }
>>> formset = FormSet(data, instance=repository)
>>> formset.is_valid()
False
>>> formset.errors
[{'__all__': [u'Revision with this Repository and Revision already exists.']}]

# unique_together with inlineformset_factory with overridden form fields
# Also see #9494

>>> FormSet = inlineformset_factory(Repository, Revision, fields=('revision',), extra=1)
>>> data = {
...     'revision_set-TOTAL_FORMS': '1',
...     'revision_set-INITIAL_FORMS': '0',
...     'revision_set-MAX_NUM_FORMS': '',
...     'revision_set-0-repository': repository.pk,
...     'revision_set-0-revision': '146239817507f148d448db38840db7c3cbf47c76',
...     'revision_set-0-DELETE': '',
... }
>>> formset = FormSet(data, instance=repository)
>>> formset.is_valid()
False

# Use of callable defaults (see bug #7975).

>>> person = Person.objects.create(name='Ringo')
>>> FormSet = inlineformset_factory(Person, Membership, can_delete=False, extra=1)
>>> formset = FormSet(instance=person)

# Django will render a hidden field for model fields that have a callable
# default. This is required to ensure the value is tested for change correctly
# when determine what extra forms have changed to save.

>>> form = formset.forms[0] # this formset only has one form
>>> now = form.fields['date_joined'].initial()
>>> print form.as_p()
<p><label for="id_membership_set-0-date_joined">Date joined:</label> <input type="text" name="membership_set-0-date_joined" value="..." id="id_membership_set-0-date_joined" /><input type="hidden" name="initial-membership_set-0-date_joined" value="..." id="initial-membership_set-0-id_membership_set-0-date_joined" /></p>
<p><label for="id_membership_set-0-karma">Karma:</label> <input type="text" name="membership_set-0-karma" id="id_membership_set-0-karma" /><input type="hidden" name="membership_set-0-person" value="1" id="id_membership_set-0-person" /><input type="hidden" name="membership_set-0-id" id="id_membership_set-0-id" /></p>

# test for validation with callable defaults. Validations rely on hidden fields

>>> data = {
...     'membership_set-TOTAL_FORMS': '1',
...     'membership_set-INITIAL_FORMS': '0',
...     'membership_set-MAX_NUM_FORMS': '',
...     'membership_set-0-date_joined': unicode(now.strftime('%Y-%m-%d %H:%M:%S')),
...     'initial-membership_set-0-date_joined': unicode(now.strftime('%Y-%m-%d %H:%M:%S')),
...     'membership_set-0-karma': '',
... }
>>> formset = FormSet(data, instance=person)
>>> formset.is_valid()
True

# now test for when the data changes

>>> one_day_later = now + datetime.timedelta(days=1)
>>> filled_data = {
...     'membership_set-TOTAL_FORMS': '1',
...     'membership_set-INITIAL_FORMS': '0',
...     'membership_set-MAX_NUM_FORMS': '',
...     'membership_set-0-date_joined': unicode(one_day_later.strftime('%Y-%m-%d %H:%M:%S')),
...     'initial-membership_set-0-date_joined': unicode(now.strftime('%Y-%m-%d %H:%M:%S')),
...     'membership_set-0-karma': '',
... }
>>> formset = FormSet(filled_data, instance=person)
>>> formset.is_valid()
False

# now test with split datetime fields

>>> class MembershipForm(forms.ModelForm):
...     date_joined = forms.SplitDateTimeField(initial=now)
...     class Meta:
...         model = Membership
...     def __init__(self, **kwargs):
...         super(MembershipForm, self).__init__(**kwargs)
...         self.fields['date_joined'].widget = forms.SplitDateTimeWidget()

>>> FormSet = inlineformset_factory(Person, Membership, form=MembershipForm, can_delete=False, extra=1)
>>> data = {
...     'membership_set-TOTAL_FORMS': '1',
...     'membership_set-INITIAL_FORMS': '0',
...     'membership_set-MAX_NUM_FORMS': '',
...     'membership_set-0-date_joined_0': unicode(now.strftime('%Y-%m-%d')),
...     'membership_set-0-date_joined_1': unicode(now.strftime('%H:%M:%S')),
...     'initial-membership_set-0-date_joined': unicode(now.strftime('%Y-%m-%d %H:%M:%S')),
...     'membership_set-0-karma': '',
... }
>>> formset = FormSet(data, instance=person)
>>> formset.is_valid()
True

# inlineformset_factory tests with fk having null=True. see #9462.
# create some data that will exbit the issue
>>> team = Team.objects.create(name=u"Red Vipers")
>>> Player(name="Timmy").save()
>>> Player(name="Bobby", team=team).save()

>>> PlayerInlineFormSet = inlineformset_factory(Team, Player)
>>> formset = PlayerInlineFormSet()
>>> formset.get_queryset()
[]

>>> formset = PlayerInlineFormSet(instance=team)
>>> formset.get_queryset()
[<Player: Bobby>]

# a formset for a Model that has a custom primary key that still needs to be
# added to the formset automatically
>>> FormSet = modelformset_factory(ClassyMexicanRestaurant, fields=["tacos_are_yummy"])
>>> sorted(FormSet().forms[0].fields.keys())
['restaurant', 'tacos_are_yummy']

# Prevent duplicates from within the same formset
>>> FormSet = modelformset_factory(Product, extra=2)
>>> data = {
...     'form-TOTAL_FORMS': 2,
...     'form-INITIAL_FORMS': 0,
...     'form-MAX_NUM_FORMS': '',
...     'form-0-slug': 'red_car',
...     'form-1-slug': 'red_car',
... }
>>> formset = FormSet(data)
>>> formset.is_valid()
False
>>> formset._non_form_errors
[u'Please correct the duplicate data for slug.']

>>> FormSet = modelformset_factory(Price, extra=2)
>>> data = {
...     'form-TOTAL_FORMS': 2,
...     'form-INITIAL_FORMS': 0,
...     'form-MAX_NUM_FORMS': '',
...     'form-0-price': '25',
...     'form-0-quantity': '7',
...     'form-1-price': '25',
...     'form-1-quantity': '7',
... }
>>> formset = FormSet(data)
>>> formset.is_valid()
False
>>> formset._non_form_errors
[u'Please correct the duplicate data for price and quantity, which must be unique.']

# Only the price field is specified, this should skip any unique checks since
# the unique_together is not fulfilled. This will fail with a KeyError if broken.
>>> FormSet = modelformset_factory(Price, fields=("price",), extra=2)
>>> data = {
...     'form-TOTAL_FORMS': '2',
...     'form-INITIAL_FORMS': '0',
...     'form-MAX_NUM_FORMS': '',
...     'form-0-price': '24',
...     'form-1-price': '24',
... }
>>> formset = FormSet(data)
>>> formset.is_valid()
True

>>> FormSet = inlineformset_factory(Author, Book, extra=0)
>>> author = Author.objects.order_by('id')[0]
>>> book_ids = author.book_set.values_list('id', flat=True)
>>> data = {
...     'book_set-TOTAL_FORMS': '2',
...     'book_set-INITIAL_FORMS': '2',
...     'book_set-MAX_NUM_FORMS': '',
...
...     'book_set-0-title': 'The 2008 Election',
...     'book_set-0-author': str(author.id),
...     'book_set-0-id': str(book_ids[0]),
...
...     'book_set-1-title': 'The 2008 Election',
...     'book_set-1-author': str(author.id),
...     'book_set-1-id': str(book_ids[1]),
... }
>>> formset = FormSet(data=data, instance=author)
>>> formset.is_valid()
False
>>> formset._non_form_errors
[u'Please correct the duplicate data for title.']
>>> formset.errors
[{}, {'__all__': u'Please correct the duplicate values below.'}]

>>> FormSet = modelformset_factory(Post, extra=2)
>>> data = {
...     'form-TOTAL_FORMS': '2',
...     'form-INITIAL_FORMS': '0',
...     'form-MAX_NUM_FORMS': '',
...
...     'form-0-title': 'blah',
...     'form-0-slug': 'Morning',
...     'form-0-subtitle': 'foo',
...     'form-0-posted': '2009-01-01',
...     'form-1-title': 'blah',
...     'form-1-slug': 'Morning in Prague',
...     'form-1-subtitle': 'rawr',
...     'form-1-posted': '2009-01-01'
... }
>>> formset = FormSet(data)
>>> formset.is_valid()
False
>>> formset._non_form_errors
[u'Please correct the duplicate data for title which must be unique for the date in posted.']
>>> formset.errors
[{}, {'__all__': u'Please correct the duplicate values below.'}]

>>> data = {
...     'form-TOTAL_FORMS': '2',
...     'form-INITIAL_FORMS': '0',
...     'form-MAX_NUM_FORMS': '',
...
...     'form-0-title': 'foo',
...     'form-0-slug': 'Morning in Prague',
...     'form-0-subtitle': 'foo',
...     'form-0-posted': '2009-01-01',
...     'form-1-title': 'blah',
...     'form-1-slug': 'Morning in Prague',
...     'form-1-subtitle': 'rawr',
...     'form-1-posted': '2009-08-02'
... }
>>> formset = FormSet(data)
>>> formset.is_valid()
False
>>> formset._non_form_errors
[u'Please correct the duplicate data for slug which must be unique for the year in posted.']

>>> data = {
...     'form-TOTAL_FORMS': '2',
...     'form-INITIAL_FORMS': '0',
...     'form-MAX_NUM_FORMS': '',
...
...     'form-0-title': 'foo',
...     'form-0-slug': 'Morning in Prague',
...     'form-0-subtitle': 'rawr',
...     'form-0-posted': '2008-08-01',
...     'form-1-title': 'blah',
...     'form-1-slug': 'Prague',
...     'form-1-subtitle': 'rawr',
...     'form-1-posted': '2009-08-02'
... }
>>> formset = FormSet(data)
>>> formset.is_valid()
False
>>> formset._non_form_errors
[u'Please correct the duplicate data for subtitle which must be unique for the month in posted.']
"""}

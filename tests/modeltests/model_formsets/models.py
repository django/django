from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class Book(models.Model):
    author = models.ForeignKey(Author)
    title = models.CharField(max_length=100)

    def __unicode__(self):
        return self.title


__test__ = {'API_TESTS': """

>>> from django.newforms.models import _modelformset_factory

>>> qs = Author.objects.all()
>>> AuthorFormSet = _modelformset_factory(Author, extra=3)

>>> formset = AuthorFormSet(queryset=qs)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_form-0-name">Name:</label> <input id="id_form-0-name" type="text" name="form-0-name" maxlength="100" /><input type="hidden" name="form-0-id" id="id_form-0-id" /></p>
<p><label for="id_form-1-name">Name:</label> <input id="id_form-1-name" type="text" name="form-1-name" maxlength="100" /><input type="hidden" name="form-1-id" id="id_form-1-id" /></p>
<p><label for="id_form-2-name">Name:</label> <input id="id_form-2-name" type="text" name="form-2-name" maxlength="100" /><input type="hidden" name="form-2-id" id="id_form-2-id" /></p>

>>> data = {
...     'form-TOTAL_FORMS': '3', # the number of forms rendered
...     'form-INITIAL_FORMS': '0', # the number of forms with initial data
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
>>> AuthorFormSet = _modelformset_factory(Author, extra=1, can_delete=False)

>>> formset = AuthorFormSet(queryset=qs)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_form-0-name">Name:</label> <input id="id_form-0-name" type="text" name="form-0-name" value="Arthur Rimbaud" maxlength="100" /><input type="hidden" name="form-0-id" value="2" id="id_form-0-id" /></p>
<p><label for="id_form-1-name">Name:</label> <input id="id_form-1-name" type="text" name="form-1-name" value="Charles Baudelaire" maxlength="100" /><input type="hidden" name="form-1-id" value="1" id="id_form-1-id" /></p>
<p><label for="id_form-2-name">Name:</label> <input id="id_form-2-name" type="text" name="form-2-name" maxlength="100" /><input type="hidden" name="form-2-id" id="id_form-2-id" /></p>


>>> data = {
...     'form-TOTAL_FORMS': '3', # the number of forms rendered
...     'form-INITIAL_FORMS': '2', # the number of forms with initial data
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
>>> AuthorFormSet = _modelformset_factory(Author, extra=1, can_delete=True)

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

# Inline Formsets ############################################################

We can also create a formset that is tied to a parent model. This is how the
admin system's edit inline functionality works.

>>> from django.newforms.models import _inlineformset_factory

>>> AuthorBooksFormSet = _inlineformset_factory(Author, Book, can_delete=False, extra=3)
>>> author = Author.objects.get(name='Charles Baudelaire')

>>> formset = AuthorBooksFormSet(instance=author)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_book_set-0-title">Title:</label> <input id="id_book_set-0-title" type="text" name="book_set-0-title" maxlength="100" /><input type="hidden" name="book_set-0-id" id="id_book_set-0-id" /></p>
<p><label for="id_book_set-1-title">Title:</label> <input id="id_book_set-1-title" type="text" name="book_set-1-title" maxlength="100" /><input type="hidden" name="book_set-1-id" id="id_book_set-1-id" /></p>
<p><label for="id_book_set-2-title">Title:</label> <input id="id_book_set-2-title" type="text" name="book_set-2-title" maxlength="100" /><input type="hidden" name="book_set-2-id" id="id_book_set-2-id" /></p>

>>> data = {
...     'book_set-TOTAL_FORMS': '3', # the number of forms rendered
...     'book_set-INITIAL_FORMS': '0', # the number of forms with initial data
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

>>> AuthorBooksFormSet = _inlineformset_factory(Author, Book, can_delete=False, extra=2)
>>> author = Author.objects.get(name='Charles Baudelaire')

>>> formset = AuthorBooksFormSet(instance=author)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_book_set-0-title">Title:</label> <input id="id_book_set-0-title" type="text" name="book_set-0-title" value="Les Fleurs du Mal" maxlength="100" /><input type="hidden" name="book_set-0-id" value="1" id="id_book_set-0-id" /></p>
<p><label for="id_book_set-1-title">Title:</label> <input id="id_book_set-1-title" type="text" name="book_set-1-title" maxlength="100" /><input type="hidden" name="book_set-1-id" id="id_book_set-1-id" /></p>
<p><label for="id_book_set-2-title">Title:</label> <input id="id_book_set-2-title" type="text" name="book_set-2-title" maxlength="100" /><input type="hidden" name="book_set-2-id" id="id_book_set-2-id" /></p>

>>> data = {
...     'book_set-TOTAL_FORMS': '3', # the number of forms rendered
...     'book_set-INITIAL_FORMS': '1', # the number of forms with initial data
...     'book_set-0-id': '1',
...     'book_set-0-title': 'Les Fleurs du Mal',
...     'book_set-1-title': 'Le Spleen de Paris',
...     'book_set-2-title': '',
... }

>>> formset = AuthorBooksFormSet(data, instance=author)
>>> formset.is_valid()
True

>>> formset.save()
[<Book: Le Spleen de Paris>]

As you can see, 'Le Spleen de Paris' is now a book belonging to Charles Baudelaire.

>>> for book in author.book_set.order_by('title'):
...     print book.title
Le Spleen de Paris
Les Fleurs du Mal

"""}

========================
Model instance reference
========================

.. currentmodule:: django.db.models

This document describes the details of the ``Model`` API. It builds on the
material presented in the :doc:`model </topics/db/models>` and :doc:`database
query </topics/db/queries>` guides, so you'll probably want to read and
understand those documents before reading this one.

Throughout this reference we'll use the :ref:`example Weblog models
<queryset-model-example>` presented in the :doc:`database query guide
</topics/db/queries>`.

Creating objects
================

To create a new instance of a model, just instantiate it like any other Python
class:

.. class:: Model(**kwargs)

The keyword arguments are simply the names of the fields you've defined on your
model. Note that instantiating a model in no way touches your database; for
that, you need to :meth:`~Model.save()`.

.. note::

    You may be tempted to customize the model by overriding the ``__init__``
    method. If you do so, however, take care not to change the calling
    signature as any change may prevent the model instance from being saved.
    Rather than overriding ``__init__``, try using one of these approaches:

    1. Add a classmethod on the model class::

        class Book(models.Model):
            title = models.CharField(max_length=100)

            @classmethod
            def create(cls, title):
                book = cls(title=title)
                # do something with the book
                return book

        book = Book.create("Pride and Prejudice")

    2. Add a method on a custom manager (usually preferred)::

        class BookManager(models.Manager):
            def create_book(self, title):
                book = self.create(title=title)
                # do something with the book
                return book

        class Book(models.Model):
            title = models.CharField(max_length=100)

            objects = BookManager()

        book = Book.objects.create_book("Pride and Prejudice")

.. _validating-objects:

Validating objects
==================

There are three steps involved in validating a model:

1. Validate the model fields - :meth:`Model.clean_fields()`
2. Validate the model as a whole - :meth:`Model.clean()`
3. Validate the field uniqueness - :meth:`Model.validate_unique()`

All three steps are performed when you call a model's
:meth:`~Model.full_clean()` method.

When you use a :class:`~django.forms.ModelForm`, the call to
:meth:`~django.forms.Form.is_valid()` will perform these validation steps for
all the fields that are included on the form. See the :doc:`ModelForm
documentation </topics/forms/modelforms>` for more information. You should only
need to call a model's :meth:`~Model.full_clean()` method if you plan to handle
validation errors yourself, or if you have excluded fields from the
:class:`~django.forms.ModelForm` that require validation.

.. method:: Model.full_clean(exclude=None)

This method calls :meth:`Model.clean_fields()`, :meth:`Model.clean()`, and
:meth:`Model.validate_unique()`, in that order and raises a
:exc:`~django.core.exceptions.ValidationError` that has a ``message_dict``
attribute containing errors from all three stages.

The optional ``exclude`` argument can be used to provide a list of field names
that can be excluded from validation and cleaning.
:class:`~django.forms.ModelForm` uses this argument to exclude fields that
aren't present on your form from being validated since any errors raised could
not be corrected by the user.

Note that ``full_clean()`` will *not* be called automatically when you call
your model's :meth:`~Model.save()` method, nor as a result of
:class:`~django.forms.ModelForm` validation. In the case of
:class:`~django.forms.ModelForm` validation, :meth:`Model.clean_fields()`,
:meth:`Model.clean()`, and :meth:`Model.validate_unique()` are all called
individually.

You'll need to call ``full_clean`` manually when you want to run one-step model
validation for your own manually created models. For example::

    try:
        article.full_clean()
    except ValidationError as e:
        # Do something based on the errors contained in e.message_dict.
        # Display them to a user, or handle them programatically.
        pass

The first step ``full_clean()`` performs is to clean each individual field.

.. method:: Model.clean_fields(exclude=None)

This method will validate all fields on your model. The optional ``exclude``
argument lets you provide a list of field names to exclude from validation. It
will raise a :exc:`~django.core.exceptions.ValidationError` if any fields fail
validation.

The second step ``full_clean()`` performs is to call :meth:`Model.clean()`.
This method should be overridden to perform custom validation on your model.

.. method:: Model.clean()

This method should be used to provide custom model validation, and to modify
attributes on your model if desired. For instance, you could use it to
automatically provide a value for a field, or to do validation that requires
access to more than a single field::

    def clean(self):
        from django.core.exceptions import ValidationError
        # Don't allow draft entries to have a pub_date.
        if self.status == 'draft' and self.pub_date is not None:
            raise ValidationError('Draft entries may not have a publication date.')
        # Set the pub_date for published items if it hasn't been set already.
        if self.status == 'published' and self.pub_date is None:
            self.pub_date = datetime.date.today()

Any :exc:`~django.core.exceptions.ValidationError` exceptions raised by
``Model.clean()`` will be stored in a special key error dictionary key,
``NON_FIELD_ERRORS``, that is used for errors that are tied to the entire model
instead of to a specific field::

    from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
    try:
        article.full_clean()
    except ValidationError as e:
        non_field_errors = e.message_dict[NON_FIELD_ERRORS]

Finally, ``full_clean()`` will check any unique constraints on your model.

.. method:: Model.validate_unique(exclude=None)

This method is similar to :meth:`~Model.clean_fields`, but validates all
uniqueness constraints on your model instead of individual field values. The
optional ``exclude`` argument allows you to provide a list of field names to
exclude from validation. It will raise a
:exc:`~django.core.exceptions.ValidationError` if any fields fail validation.

Note that if you provide an ``exclude`` argument to ``validate_unique()``, any
:attr:`~django.db.models.Options.unique_together` constraint involving one of
the fields you provided will not be checked.


Saving objects
==============

To save an object back to the database, call ``save()``:

.. method:: Model.save([force_insert=False, force_update=False, using=DEFAULT_DB_ALIAS, update_fields=None])

If you want customized saving behavior, you can override this ``save()``
method. See :ref:`overriding-model-methods` for more details.

The model save process also has some subtleties; see the sections below.

Auto-incrementing primary keys
------------------------------

If a model has an :class:`~django.db.models.AutoField` — an auto-incrementing
primary key — then that auto-incremented value will be calculated and saved as
an attribute on your object the first time you call ``save()``::

    >>> b2 = Blog(name='Cheddar Talk', tagline='Thoughts on cheese.')
    >>> b2.id     # Returns None, because b doesn't have an ID yet.
    >>> b2.save()
    >>> b2.id     # Returns the ID of your new object.

There's no way to tell what the value of an ID will be before you call
``save()``, because that value is calculated by your database, not by Django.

For convenience, each model has an :class:`~django.db.models.AutoField` named
``id`` by default unless you explicitly specify ``primary_key=True`` on a field
in your model. See the documentation for :class:`~django.db.models.AutoField`
for more details.

The ``pk`` property
~~~~~~~~~~~~~~~~~~~

.. attribute:: Model.pk

Regardless of whether you define a primary key field yourself, or let Django
supply one for you, each model will have a property called ``pk``. It behaves
like a normal attribute on the model, but is actually an alias for whichever
attribute is the primary key field for the model. You can read and set this
value, just as you would for any other attribute, and it will update the
correct field in the model.

Explicitly specifying auto-primary-key values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If a model has an :class:`~django.db.models.AutoField` but you want to define a
new object's ID explicitly when saving, just define it explicitly before
saving, rather than relying on the auto-assignment of the ID::

    >>> b3 = Blog(id=3, name='Cheddar Talk', tagline='Thoughts on cheese.')
    >>> b3.id     # Returns 3.
    >>> b3.save()
    >>> b3.id     # Returns 3.

If you assign auto-primary-key values manually, make sure not to use an
already-existing primary-key value! If you create a new object with an explicit
primary-key value that already exists in the database, Django will assume you're
changing the existing record rather than creating a new one.

Given the above ``'Cheddar Talk'`` blog example, this example would override the
previous record in the database::

    b4 = Blog(id=3, name='Not Cheddar', tagline='Anything but cheese.')
    b4.save()  # Overrides the previous blog with ID=3!

See `How Django knows to UPDATE vs. INSERT`_, below, for the reason this
happens.

Explicitly specifying auto-primary-key values is mostly useful for bulk-saving
objects, when you're confident you won't have primary-key collision.

What happens when you save?
---------------------------

When you save an object, Django performs the following steps:

1. **Emit a pre-save signal.** The :doc:`signal </ref/signals>`
   :attr:`django.db.models.signals.pre_save` is sent, allowing any
   functions listening for that signal to take some customized
   action.

2. **Pre-process the data.** Each field on the object is asked to
   perform any automated data modification that the field may need
   to perform.

   Most fields do *no* pre-processing — the field data is kept as-is.
   Pre-processing is only used on fields that have special behavior.  For
   example, if your model has a :class:`~django.db.models.DateField` with
   ``auto_now=True``, the pre-save phase will alter the data in the object
   to ensure that the date field contains the current date stamp. (Our
   documentation doesn't yet include a list of all the fields with this
   "special behavior.")

3. **Prepare the data for the database.** Each field is asked to provide
   its current value in a data type that can be written to the database.

   Most fields require *no* data preparation. Simple data types, such as
   integers and strings, are 'ready to write' as a Python object. However,
   more complex data types often require some modification.

   For example, :class:`~django.db.models.DateField` fields use a Python
   ``datetime`` object to store data. Databases don't store ``datetime``
   objects, so the field value must be converted into an ISO-compliant date
   string for insertion into the database.

4. **Insert the data into the database.** The pre-processed, prepared
   data is then composed into an SQL statement for insertion into the
   database.

5. **Emit a post-save signal.** The signal
   :attr:`django.db.models.signals.post_save` is sent, allowing
   any functions listening for that signal to take some customized
   action.

How Django knows to UPDATE vs. INSERT
-------------------------------------

You may have noticed Django database objects use the same ``save()`` method
for creating and changing objects. Django abstracts the need to use ``INSERT``
or ``UPDATE`` SQL statements. Specifically, when you call ``save()``, Django
follows this algorithm:

* If the object's primary key attribute is set to a value that evaluates to
  ``True`` (i.e., a value other than ``None`` or the empty string), Django
  executes a ``SELECT`` query to determine whether a record with the given
  primary key already exists.
* If the record with the given primary key does already exist, Django
  executes an ``UPDATE`` query.
* If the object's primary key attribute is *not* set, or if it's set but a
  record doesn't exist, Django executes an ``INSERT``.

The one gotcha here is that you should be careful not to specify a primary-key
value explicitly when saving new objects, if you cannot guarantee the
primary-key value is unused. For more on this nuance, see `Explicitly specifying
auto-primary-key values`_ above and `Forcing an INSERT or UPDATE`_ below.

.. _ref-models-force-insert:

Forcing an INSERT or UPDATE
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In some rare circumstances, it's necessary to be able to force the
:meth:`~Model.save()` method to perform an SQL ``INSERT`` and not fall back to
doing an ``UPDATE``. Or vice-versa: update, if possible, but not insert a new
row. In these cases you can pass the ``force_insert=True`` or
``force_update=True`` parameters to the :meth:`~Model.save()` method.
Obviously, passing both parameters is an error: you cannot both insert *and*
update at the same time!

It should be very rare that you'll need to use these parameters. Django will
almost always do the right thing and trying to override that will lead to
errors that are difficult to track down. This feature is for advanced use
only.

Using ``update_fields`` will force an update similarly to ``force_update``.

Updating attributes based on existing fields
--------------------------------------------

Sometimes you'll need to perform a simple arithmetic task on a field, such
as incrementing or decrementing the current value. The obvious way to
achieve this is to do something like::

    >>> product = Product.objects.get(name='Venezuelan Beaver Cheese')
    >>> product.number_sold += 1
    >>> product.save()

If the old ``number_sold`` value retrieved from the database was 10, then
the value of 11 will be written back to the database.

This sequence has a standard update problem in that it contains a race
condition. If another thread of execution has already saved an updated value
after the current thread retrieved the old value, the current thread will only
save the old value plus one, rather than the new (current) value plus one.

The process can be made robust and slightly faster by expressing the update
relative to the original field value, rather than as an explicit assignment of
a new value. Django provides :ref:`F() expressions <query-expressions>` for
performing this kind of relative update. Using ``F()`` expressions, the
previous example is expressed as::

    >>> from django.db.models import F
    >>> product = Product.objects.get(name='Venezuelan Beaver Cheese')
    >>> product.number_sold = F('number_sold') + 1
    >>> product.save()

This approach doesn't use the initial value from the database. Instead, it
makes the database do the update based on whatever value is current at the time
that the :meth:`~Model.save()` is executed.

Once the object has been saved, you must reload the object in order to access
the actual value that was applied to the updated field::

    >>> product = Products.objects.get(pk=product.pk)
    >>> print(product.number_sold)
    42

For more details, see the documentation on :ref:`F() expressions
<query-expressions>` and their :ref:`use in update queries
<topics-db-queries-update>`.

Specifying which fields to save
-------------------------------

.. versionadded:: 1.5

If ``save()`` is passed a list of field names in keyword argument
``update_fields``, only the fields named in that list will be updated.
This may be desirable if you want to update just one or a few fields on
an object. There will be a slight performance benefit from preventing
all of the model fields from being updated in the database. For example::

    product.name = 'Name changed again'
    product.save(update_fields=['name'])

The ``update_fields`` argument can be any iterable containing strings. An
empty ``update_fields`` iterable will skip the save. A value of None will
perform an update on all fields.

Specifying ``update_fields`` will force an update.

When saving a model fetched through deferred model loading
(:meth:`~django.db.models.query.QuerySet.only()` or
:meth:`~django.db.models.query.QuerySet.defer()`) only the fields loaded
from the DB will get updated. In effect there is an automatic
``update_fields`` in this case. If you assign or change any deferred field
value, the field will be added to the updated fields.

Deleting objects
================

.. method:: Model.delete([using=DEFAULT_DB_ALIAS])

Issues a SQL ``DELETE`` for the object. This only deletes the object in the
database; the Python instance will still exist and will still have data in
its fields.

For more details, including how to delete objects in bulk, see
:ref:`topics-db-queries-delete`.

If you want customized deletion behavior, you can override the ``delete()``
method. See :ref:`overriding-model-methods` for more details.

.. _model-instance-methods:

Other model instance methods
============================

A few object methods have special purposes.

``__unicode__``
---------------

.. method:: Model.__unicode__()

The ``__unicode__()`` method is called whenever you call ``unicode()`` on an
object. Django uses ``unicode(obj)`` (or the related function, :meth:`str(obj)
<Model.__str__>`) in a number of places. Most notably, to display an object in
the Django admin site and as the value inserted into a template when it
displays an object. Thus, you should always return a nice, human-readable
representation of the model from the ``__unicode__()`` method.

For example::

    class Person(models.Model):
        first_name = models.CharField(max_length=50)
        last_name = models.CharField(max_length=50)

        def __unicode__(self):
            return u'%s %s' % (self.first_name, self.last_name)

If you define a ``__unicode__()`` method on your model and not a
:meth:`~Model.__str__()` method, Django will automatically provide you with a
:meth:`~Model.__str__()` that calls ``__unicode__()`` and then converts the
result correctly to a UTF-8 encoded string object. This is recommended
development practice: define only ``__unicode__()`` and let Django take care of
the conversion to string objects when required.

``__str__``
-----------

.. method:: Model.__str__()

The ``__str__()`` method is called whenever you call ``str()`` on an object. The main use for this method directly inside Django is when the ``repr()`` output of a model is displayed anywhere (for example, in debugging output).
Thus, you should return a nice, human-readable string for the object's
``__str__()``.  It isn't required to put ``__str__()`` methods everywhere if you have sensible :meth:`~Model.__unicode__()` methods.

The previous :meth:`~Model.__unicode__()` example could be similarly written
using ``__str__()`` like this::

    class Person(models.Model):
        first_name = models.CharField(max_length=50)
        last_name = models.CharField(max_length=50)

        def __str__(self):
            # Note use of django.utils.encoding.force_bytes() here because
            # first_name and last_name will be unicode strings.
            return force_bytes('%s %s' % (self.first_name, self.last_name))

``get_absolute_url``
--------------------

.. method:: Model.get_absolute_url()

Define a ``get_absolute_url()`` method to tell Django how to calculate the
canonical URL for an object. To callers, this method should appear to return a
string that can be used to refer to the object over HTTP.

For example::

    def get_absolute_url(self):
        return "/people/%i/" % self.id

(Whilst this code is correct and simple, it may not be the most portable way to
write this kind of method. The :func:`~django.core.urlresolvers.reverse`
function is usually the best approach.)

For example::

    def get_absolute_url(self):
        return reverse('people.views.details', args=[str(self.id)])

One place Django uses ``get_absolute_url()`` is in the admin app. If an object
defines this method, the object-editing page will have a "View on site" link
that will jump you directly to the object's public view, as given by
``get_absolute_url()``.

Similarly, a couple of other bits of Django, such as the :doc:`syndication feed
framework </ref/contrib/syndication>`, use ``get_absolute_url()`` when it is
defined. If it makes sense for your model's instances to each have a unique
URL, you should define ``get_absolute_url()``.

It's good practice to use ``get_absolute_url()`` in templates, instead of
hard-coding your objects' URLs. For example, this template code is bad:

.. code-block:: html+django

    <!-- BAD template code. Avoid! -->
    <a href="/people/{{ object.id }}/">{{ object.name }}</a>

This template code is much better:

.. code-block:: html+django

    <a href="{{ object.get_absolute_url }}">{{ object.name }}</a>

The logic here is that if you change the URL structure of your objects, even
for something simple such as correcting a spelling error, you don't want to
have to track down every place that the URL might be created. Specify it once,
in ``get_absolute_url()`` and have all your other code call that one place.

.. note::
    The string you return from ``get_absolute_url()`` **must** contain only
    ASCII characters (required by the URI specfication, :rfc:`2396`) and be
    URL-encoded, if necessary.

    Code and templates calling ``get_absolute_url()`` should be able to use the
    result directly without any further processing. You may wish to use the
    ``django.utils.encoding.iri_to_uri()`` function to help with this if you
    are using unicode strings containing characters outside the ASCII range at
    all.

The ``permalink`` decorator
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::

    The ``permalink`` decorator is no longer recommended. You should use
    :func:`~django.core.urlresolvers.reverse` in the body of your
    ``get_absolute_url`` method instead.

In early versions of Django, there wasn't an easy way to use URLs defined in
URLconf file inside :meth:`~django.db.models.Model.get_absolute_url`. That
meant you would need to define the URL both in URLConf and
:meth:`~django.db.models.Model.get_absolute_url`. The ``permalink`` decorator
was added to overcome this DRY principle violation. However, since the
introduction of :func:`~django.core.urlresolvers.reverse` there is no
reason to use ``permalink`` any more.

.. function:: permalink()

This decorator takes the name of a URL pattern (either a view name or a URL
pattern name) and a list of position or keyword arguments and uses the URLconf
patterns to construct the correct, full URL. It returns a string for the
correct URL, with all parameters substituted in the correct positions.

The ``permalink`` decorator is a Python-level equivalent to the :ttag:`url`
template tag and a high-level wrapper for the
:func:`~django.core.urlresolvers.reverse` function.

An example should make it clear how to use ``permalink()``. Suppose your URLconf
contains a line such as::

    (r'^people/(\d+)/$', 'people.views.details'),

...your model could have a :meth:`~django.db.models.Model.get_absolute_url`
method that looked like this::

    from django.db import models

    @models.permalink
    def get_absolute_url(self):
        return ('people.views.details', [str(self.id)])

Similarly, if you had a URLconf entry that looked like::

    (r'/archive/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/$', archive_view)

...you could reference this using ``permalink()`` as follows::

    @models.permalink
    def get_absolute_url(self):
        return ('archive_view', (), {
            'year': self.created.year,
            'month': self.created.strftime('%m'),
            'day': self.created.strftime('%d')})

Notice that we specify an empty sequence for the second parameter in this case,
because we only want to pass keyword parameters, not positional ones.

In this way, you're associating the model's absolute path with the view that is
used to display it, without repeating the view's URL information anywhere. You
can still use the :meth:`~django.db.models.Model.get_absolute_url()` method in
templates, as before.

In some cases, such as the use of generic views or the re-use of custom views
for multiple models, specifying the view function may confuse the reverse URL
matcher (because multiple patterns point to the same view). For that case,
Django has :ref:`named URL patterns <naming-url-patterns>`. Using a named URL
pattern, it's possible to give a name to a pattern, and then reference the name
rather than the view function. A named URL pattern is defined by replacing the
pattern tuple by a call to the ``url`` function)::

    from django.conf.urls import url

    url(r'^people/(\d+)/$', 'blog_views.generic_detail', name='people_view'),

...and then using that name to perform the reverse URL resolution instead
of the view name::

    from django.db import models

    @models.permalink
    def get_absolute_url(self):
        return ('people_view', [str(self.id)])

More details on named URL patterns are in the :doc:`URL dispatch documentation
</topics/http/urls>`.

Extra instance methods
======================

In addition to :meth:`~Model.save()`, :meth:`~Model.delete()`, a model object
might have some of the following methods:

.. method:: Model.get_FOO_display()

For every field that has :attr:`~django.db.models.Field.choices` set, the
object will have a ``get_FOO_display()`` method, where ``FOO`` is the name of
the field. This method returns the "human-readable" value of the field.

For example::

    from django.db import models

    class Person(models.Model):
        SHIRT_SIZES = (
            (u'S', u'Small'),
            (u'M', u'Medium'),
            (u'L', u'Large'),
        )
        name = models.CharField(max_length=60)
        shirt_size = models.CharField(max_length=2, choices=SHIRT_SIZES)

::

    >>> p = Person(name="Fred Flintstone", shirt_size="L")
    >>> p.save()
    >>> p.shirt_size
    u'L'
    >>> p.get_shirt_size_display()
    u'Large'

.. method:: Model.get_next_by_FOO(\**kwargs)
.. method:: Model.get_previous_by_FOO(\**kwargs)

For every :class:`~django.db.models.DateField` and
:class:`~django.db.models.DateTimeField` that does not have :attr:`null=True
<django.db.models.Field.null>`, the object will have ``get_next_by_FOO()`` and
``get_previous_by_FOO()`` methods, where ``FOO`` is the name of the field. This
returns the next and previous object with respect to the date field, raising
a :exc:`~django.core.exceptions.DoesNotExist` exception when appropriate.

Both methods accept optional keyword arguments, which should be in the format
described in :ref:`Field lookups <field-lookups>`.

Note that in the case of identical date values, these methods will use the
primary key as a tie-breaker. This guarantees that no records are skipped or
duplicated. That also means you cannot use those methods on unsaved objects.

===================
Django and doctests
===================

Doctests use Python's standard :mod:`doctest` module, which searches your
docstrings for statements that resemble a session of the Python interactive
interpreter. A full explanation of how :mod:`doctest` works is out of the scope
of this document; read Python's official documentation for the details.

.. admonition:: What's a **docstring**?

    A good explanation of docstrings (and some guidelines for using them
    effectively) can be found in :pep:`257`:

        A docstring is a string literal that occurs as the first statement in
        a module, function, class, or method definition.  Such a docstring
        becomes the ``__doc__`` special attribute of that object.

    For example, this function has a docstring that describes what it does::

        def add_two(num):
            "Return the result of adding two to the provided number."
            return num + 2

    Because tests often make great documentation, putting tests directly in
    your docstrings is an effective way to document *and* test your code.

As with unit tests, for a given Django application, the test runner looks for
doctests in two places:

* The ``models.py`` file. You can define module-level doctests and/or a
  doctest for individual models. It's common practice to put
  application-level doctests in the module docstring and model-level
  doctests in the model docstrings.

* A file called ``tests.py`` in the application directory -- i.e., the
  directory that holds ``models.py``. This file is a hook for any and all
  doctests you want to write that aren't necessarily related to models.

This example doctest is equivalent to the example given in the unittest section
above::

    # models.py

    from django.db import models

    class Animal(models.Model):
        """
        An animal that knows how to make noise

        # Create some animals
        >>> lion = Animal.objects.create(name="lion", sound="roar")
        >>> cat = Animal.objects.create(name="cat", sound="meow")

        # Make 'em speak
        >>> lion.speak()
        'The lion says "roar"'
        >>> cat.speak()
        'The cat says "meow"'
        """
        name = models.CharField(max_length=20)
        sound = models.CharField(max_length=20)

        def speak(self):
            return 'The %s says "%s"' % (self.name, self.sound)

When you :ref:`run your tests <running-tests>`, the test runner will find this
docstring, notice that portions of it look like an interactive Python session,
and execute those lines while checking that the results match.

In the case of model tests, note that the test runner takes care of creating
its own test database. That is, any test that accesses a database -- by
creating and saving model instances, for example -- will not affect your
production database. However, the database is not refreshed between doctests,
so if your doctest requires a certain state you should consider flushing the
database or loading a fixture. (See the section on :ref:`fixtures
<topics-testing-fixtures>` for more on this.) Note that to use this feature,
the database user Django is connecting as must have ``CREATE DATABASE``
rights.

For more details about :mod:`doctest`, see the Python documentation.

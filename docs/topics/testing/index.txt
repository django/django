=================
Testing in Django
=================

.. toctree::
   :hidden:

   overview
   doctests
   advanced

Automated testing is an extremely useful bug-killing tool for the modern
Web developer. You can use a collection of tests -- a **test suite** -- to
solve, or avoid, a number of problems:

* When you're writing new code, you can use tests to validate your code
  works as expected.

* When you're refactoring or modifying old code, you can use tests to
  ensure your changes haven't affected your application's behavior
  unexpectedly.

Testing a Web application is a complex task, because a Web application is made
of several layers of logic -- from HTTP-level request handling, to form
validation and processing, to template rendering. With Django's test-execution
framework and assorted utilities, you can simulate requests, insert test data,
inspect your application's output and generally verify your code is doing what
it should be doing.

The best part is, it's really easy.

Unit tests v. doctests
======================

There are two primary ways to write tests with Django, corresponding to the
two test frameworks that ship in the Python standard library. The two
frameworks are:

* **Unit tests** -- tests that are expressed as methods on a Python class
  that subclasses :class:`unittest.TestCase` or Django's customized
  :class:`~django.test.TestCase`. For example::

      import unittest

      class MyFuncTestCase(unittest.TestCase):
          def testBasic(self):
              a = ['larry', 'curly', 'moe']
              self.assertEqual(my_func(a, 0), 'larry')
              self.assertEqual(my_func(a, 1), 'curly')

* **Doctests** -- tests that are embedded in your functions' docstrings and
  are written in a way that emulates a session of the Python interactive
  interpreter. For example::

      def my_func(a_list, idx):
          """
          >>> a = ['larry', 'curly', 'moe']
          >>> my_func(a, 0)
          'larry'
          >>> my_func(a, 1)
          'curly'
          """
          return a_list[idx]

Which should I use?
-------------------

Because Django supports both of the standard Python test frameworks, it's up to
you and your tastes to decide which one to use. You can even decide to use
*both*.

For developers new to testing, however, this choice can seem confusing. Here,
then, are a few key differences to help you decide which approach is right for
you:

* If you've been using Python for a while, :mod:`doctest` will probably feel
  more "pythonic". It's designed to make writing tests as easy as possible,
  so it requires no overhead of writing classes or methods. You simply put
  tests in docstrings. This has the added advantage of serving as
  documentation (and correct documentation, at that!). However, while
  doctests are good for some simple example code, they are not very good if
  you want to produce either high quality, comprehensive tests or high
  quality documentation. Test failures are often difficult to debug
  as it can be unclear exactly why the test failed. Thus, doctests should
  generally be avoided and used primarily for documentation examples only.

* The :mod:`unittest` framework will probably feel very familiar to
  developers coming from Java. :mod:`unittest` is inspired by Java's JUnit,
  so you'll feel at home with this method if you've used JUnit or any test
  framework inspired by JUnit.

* If you need to write a bunch of tests that share similar code, then
  you'll appreciate the :mod:`unittest` framework's organization around
  classes and methods. This makes it easy to abstract common tasks into
  common methods. The framework also supports explicit setup and/or cleanup
  routines, which give you a high level of control over the environment
  in which your test cases are run.

* If you're writing tests for Django itself, you should use :mod:`unittest`.

Where to go from here
=====================

As unit tests are preferred in Django, we treat them in detail in the
:doc:`overview` document.

:doc:`doctests` describes Django-specific features when using doctests.

You can also use any *other* Python test framework, Django provides an API and
tools for that kind of integration. They are described in the
:ref:`other-testing-frameworks` section of :doc:`advanced`.

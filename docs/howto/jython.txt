========================
Running Django on Jython
========================

.. index:: Jython, Java, JVM

.. admonition:: Python 2.6 support

    Django 1.5 has dropped support for Python 2.5. Therefore, you have to use
    a Jython 2.7 alpha release if you want to use Django 1.5 with Jython.
    Please use Django 1.4 if you want to keep using Django on a stable Jython
    version.

Jython_ is an implementation of Python that runs on the Java platform (JVM).
Django runs cleanly on Jython version 2.5 or later, which means you can deploy
Django on any Java platform.

This document will get you up and running with Django on top of Jython.

.. _jython: http://www.jython.org/

Installing Jython
=================

Django works with Jython versions 2.5b3 and higher. Download Jython at 
http://www.jython.org/.

Creating a servlet container
============================

If you just want to experiment with Django, skip ahead to the next section;
Django includes a lightweight Web server you can use for testing, so you won't
need to set up anything else until you're ready to deploy Django in production.

If you want to use Django on a production site, use a Java servlet container,
such as `Apache Tomcat`_. Full JavaEE applications servers such as `GlassFish`_
or `JBoss`_ are also OK, if you need the extra features they include.

.. _`Apache Tomcat`: http://tomcat.apache.org/
.. _GlassFish: http://glassfish.java.net/
.. _JBoss: http://www.jboss.org/

Installing Django
=================

The next step is to install Django itself. This is exactly the same as
installing Django on standard Python, so see
:ref:`removing-old-versions-of-django` and :ref:`install-django-code` for
instructions.

Installing Jython platform support libraries
============================================

The `django-jython`_ project contains database backends and management commands
for Django/Jython development. Note that the builtin Django backends won't work
on top of Jython.

.. _`django-jython`: http://code.google.com/p/django-jython/

To install it, follow the `installation instructions`_ detailed on the project
Web site. Also, read the `database backends`_ documentation there.

.. _`installation instructions`: http://code.google.com/p/django-jython/wiki/Install
.. _`database backends`: http://code.google.com/p/django-jython/wiki/DatabaseBackends

Differences with Django on Jython
=================================

.. index:: JYTHONPATH

At this point, Django on Jython should behave nearly identically to Django
running on standard Python. However, are a few differences to keep in mind:

* Remember to use the ``jython`` command instead of ``python``. The
  documentation uses ``python`` for consistency, but if you're using Jython
  you'll want to mentally replace ``python`` with ``jython`` every time it
  occurs.

* Similarly, you'll need to use the ``JYTHONPATH`` environment variable
  instead of ``PYTHONPATH``.


.. _index:

====================
Django documentation
====================

.. rubric:: Everything you need to know about Django.

Getting help
============

Having trouble? We'd like to help!

* Try the :doc:`FAQ <faq/index>` -- it's got answers to many common questions.

* Looking for specific information? Try the :ref:`genindex`, :ref:`modindex` or
  the :doc:`detailed table of contents <contents>`.

* Search for information in the `archives of the django-users mailing list`_, or
  `post a question`_.

* Ask a question in the `#django IRC channel`_, or search the `IRC logs`_ to see
  if it's been asked before.

* Report bugs with Django in our `ticket tracker`_.

.. _archives of the django-users mailing list: http://groups.google.com/group/django-users/
.. _post a question: http://groups.google.com/group/django-users/
.. _#django IRC channel: irc://irc.freenode.net/django
.. _IRC logs: http://django-irc-logs.com/
.. _ticket tracker: https://code.djangoproject.com/

First steps
===========

Are you new to Django or to programming? This is the place to start!

* **From scratch:**
  :doc:`Overview <intro/overview>` |
  :doc:`Installation <intro/install>`

* **Tutorial:**
  :doc:`Part 1 <intro/tutorial01>` |
  :doc:`Part 2 <intro/tutorial02>` |
  :doc:`Part 3 <intro/tutorial03>` |
  :doc:`Part 4 <intro/tutorial04>` |
  :doc:`Part 5 <intro/tutorial05>`

* **Advanced Tutorials:**
  :doc:`How to write reusable apps <intro/reusable-apps>` |
  :doc:`Writing your first patch for Django <intro/contributing>`

The model layer
===============

Django provides an abstraction layer (the "models") for structuring and
manipulating the data of your Web application. Learn more about it below:

* **Models:**
  :doc:`Model syntax <topics/db/models>` |
  :doc:`Field types <ref/models/fields>` |
  :doc:`Meta options <ref/models/options>`

* **QuerySets:**
  :doc:`Executing queries <topics/db/queries>` |
  :doc:`QuerySet method reference <ref/models/querysets>`

* **Model instances:**
  :doc:`Instance methods <ref/models/instances>` |
  :doc:`Accessing related objects <ref/models/relations>`

* **Advanced:**
  :doc:`Managers <topics/db/managers>` |
  :doc:`Raw SQL <topics/db/sql>` |
  :doc:`Transactions <topics/db/transactions>` |
  :doc:`Aggregation <topics/db/aggregation>` |
  :doc:`Custom fields <howto/custom-model-fields>` |
  :doc:`Multiple databases <topics/db/multi-db>`

* **Other:**
  :doc:`Supported databases <ref/databases>` |
  :doc:`Legacy databases <howto/legacy-databases>` |
  :doc:`Providing initial data <howto/initial-data>` |
  :doc:`Optimize database access <topics/db/optimization>`

The view layer
==============

Django has the concept of "views" to encapsulate the logic responsible for
processing a user's request and for returning the response. Find all you need
to know about views via the links below:

* **The basics:**
  :doc:`URLconfs <topics/http/urls>` |
  :doc:`View functions <topics/http/views>` |
  :doc:`Shortcuts <topics/http/shortcuts>` |
  :doc:`Decorators <topics/http/decorators>`

* **Reference:**
  :doc:`Request/response objects <ref/request-response>` |
  :doc:`TemplateResponse objects <ref/template-response>`

* **File uploads:**
  :doc:`Overview <topics/http/file-uploads>` |
  :doc:`File objects <ref/files/file>` |
  :doc:`Storage API <ref/files/storage>` |
  :doc:`Managing files <topics/files>` |
  :doc:`Custom storage <howto/custom-file-storage>`

* **Class-based views:**
  :doc:`Overview <topics/class-based-views/index>` |
  :doc:`Built-in display views <topics/class-based-views/generic-display>` |
  :doc:`Built-in editing views <topics/class-based-views/generic-editing>` |
  :doc:`Using mixins <topics/class-based-views/mixins>` |
  :doc:`API reference <ref/class-based-views/index>` |
  :doc:`Flattened index<ref/class-based-views/flattened-index>`

* **Advanced:**
  :doc:`Generating CSV <howto/outputting-csv>` |
  :doc:`Generating PDF <howto/outputting-pdf>`

* **Middleware:**
  :doc:`Overview <topics/http/middleware>` |
  :doc:`Built-in middleware classes <ref/middleware>`

The template layer
==================

The template layer provides a designer-friendly syntax for rendering the
information to be presented to the user. Learn how this syntax can be used by
designers and how it can be extended by programmers:

* **For designers:**
  :doc:`Syntax overview <topics/templates>` |
  :doc:`Built-in tags and filters <ref/templates/builtins>` |
  :doc:`Web design helpers <ref/contrib/webdesign>` |
  :doc:`Humanization <ref/contrib/humanize>`

* **For programmers:**
  :doc:`Template API <ref/templates/api>` |
  :doc:`Custom tags and filters <howto/custom-template-tags>`

Forms
=====

Django provides a rich framework to facilitate the creation of forms and the
manipulation of form data.

* **The basics:**
  :doc:`Overview <topics/forms/index>` |
  :doc:`Form API <ref/forms/api>` |
  :doc:`Built-in fields <ref/forms/fields>` |
  :doc:`Built-in widgets <ref/forms/widgets>`

* **Advanced:**
  :doc:`Forms for models <topics/forms/modelforms>` |
  :doc:`Integrating media <topics/forms/media>` |
  :doc:`Formsets <topics/forms/formsets>` |
  :doc:`Customizing validation <ref/forms/validation>`

* **Extras:**
  :doc:`Form preview <ref/contrib/formtools/form-preview>` |
  :doc:`Form wizard <ref/contrib/formtools/form-wizard>`

The development process
=======================

Learn about the various components and tools to help you in the development and
testing of Django applications:

* **Settings:**
  :doc:`Overview <topics/settings>` |
  :doc:`Full list of settings <ref/settings>`

* **Exceptions:**
  :doc:`Overview <ref/exceptions>`

* **django-admin.py and manage.py:**
  :doc:`Overview <ref/django-admin>` |
  :doc:`Adding custom commands <howto/custom-management-commands>`

* **Testing:**
  :doc:`Introduction <topics/testing/index>` |
  :doc:`Writing and running tests <topics/testing/overview>` |
  :doc:`Advanced topics <topics/testing/advanced>` |
  :doc:`Doctests <topics/testing/doctests>`

* **Deployment:**
  :doc:`Overview <howto/deployment/index>` |
  :doc:`WSGI servers <howto/deployment/wsgi/index>` |
  :doc:`FastCGI/SCGI/AJP <howto/deployment/fastcgi>` |
  :doc:`Handling static files <howto/static-files>` |
  :doc:`Tracking code errors by email <howto/error-reporting>`

The admin
=========

Find all you need to know about the automated admin interface, one of Django's
most popular features:

* :doc:`Admin site <ref/contrib/admin/index>`
* :doc:`Admin actions <ref/contrib/admin/actions>`
* :doc:`Admin documentation generator<ref/contrib/admin/admindocs>`

Security
========

Security is a topic of paramount importance in the development of Web
applications and Django provides multiple protection tools and mechanisms:

* :doc:`Security overview <topics/security>`
* :doc:`Clickjacking protection <ref/clickjacking>`
* :doc:`Cross Site Request Forgery protection <ref/contrib/csrf>`
* :doc:`Cryptographic signing <topics/signing>`

Internationalization and localization
=====================================

Django offers a robust internationalization and localization framework to
assist you in the development of applications for multiple languages and world
regions:

* :doc:`Overview <topics/i18n/index>` |
  :doc:`Internationalization <topics/i18n/translation>` |
  :ref:`Localization <how-to-create-language-files>`
* :doc:`"Local flavor" <ref/contrib/localflavor>`
* :doc:`Time zones </topics/i18n/timezones>`

Python compatibility
====================

Django aims to be compatible with multiple different flavors and versions of
Python:

* :doc:`Jython support <howto/jython>`
* :doc:`Python 3 compatibility <topics/python3>`

Geographic framework
====================

:doc:`GeoDjango <ref/contrib/gis/index>` intends to be a world-class geographic
Web framework. Its goal is to make it as easy as possible to build GIS Web
applications and harness the power of spatially enabled data.

Common Web application tools
============================

Django offers multiple tools commonly needed in the development of Web
applications:

* :doc:`Authentication <topics/auth/index>`
* :doc:`Caching <topics/cache>`
* :doc:`Logging <topics/logging>`
* :doc:`Sending emails <topics/email>`
* :doc:`Syndication feeds (RSS/Atom) <ref/contrib/syndication>`
* :doc:`Comments <ref/contrib/comments/index>`, :doc:`comment moderation <ref/contrib/comments/moderation>` and :doc:`custom comments <ref/contrib/comments/custom>`
* :doc:`Pagination <topics/pagination>`
* :doc:`Messages framework <ref/contrib/messages>`
* :doc:`Serialization <topics/serialization>`
* :doc:`Sessions <topics/http/sessions>`
* :doc:`Sitemaps <ref/contrib/sitemaps>`
* :doc:`Static files management <ref/contrib/staticfiles>`
* :doc:`Data validation <ref/validators>`

Other core functionalities
==========================

Learn about some other core functionalities of the Django framework:

* :doc:`Conditional content processing <topics/conditional-view-processing>`
* :doc:`Content types and generic relations <ref/contrib/contenttypes>`
* :doc:`Databrowse <ref/contrib/databrowse>`
* :doc:`Flatpages <ref/contrib/flatpages>`
* :doc:`Redirects <ref/contrib/redirects>`
* :doc:`Signals <topics/signals>`
* :doc:`The sites framework <ref/contrib/sites>`
* :doc:`Unicode in Django <ref/unicode>`

The Django open-source project
==============================

Learn about the development process for the Django project itself and about how
you can contribute:

* **Community:**
  :doc:`How to get involved <internals/contributing/index>` |
  :doc:`The release process <internals/release-process>` |
  :doc:`Team of committers <internals/committers>` |
  :doc:`The Django source code repository <internals/git>` |
  :doc:`Security policies <internals/security>`

* **Design philosophies:**
  :doc:`Overview <misc/design-philosophies>`

* **Documentation:**
  :doc:`About this documentation <internals/contributing/writing-documentation>`

* **Third-party distributions:**
  :doc:`Overview <misc/distributions>`

* **Django over time:**
  :doc:`API stability <misc/api-stability>` |
  :doc:`Release notes and upgrading instructions <releases/index>` |
  :doc:`Deprecation Timeline <internals/deprecation>`

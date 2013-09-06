=================
Django Exceptions
=================


Django raises some Django specific exceptions as well as many standard
Python exceptions.

Django Core Exceptions
======================

.. module:: django.core.exceptions
    :synopsis: Django core exceptions

Django core exception classes are defined in :mod:`django.core.exceptions`.

ObjectDoesNotExist and DoesNotExist
-----------------------------------
.. exception:: DoesNotExist

    The ``DoesNotExist`` exception is raised when an object is not found for
    the given parameters of a query. Django provides a ``DoesNotExist``
    exception as an attribute of each model class to identify the class of
    object that could not be found and to allow you to catch a particular model
    class with ``try/except``.

.. exception:: ObjectDoesNotExist

    The base class for ``DoesNotExist`` exceptions; a ``try/except`` for
    ``ObjectDoesNotExist`` will catch ``DoesNotExist`` exceptions for all
    models.

    See :meth:`~django.db.models.query.QuerySet.get()` for further information
    on :exc:`ObjectDoesNotExist` and :exc:`DoesNotExist`.

MultipleObjectsReturned
-----------------------
.. exception:: MultipleObjectsReturned

    The :exc:`MultipleObjectsReturned` exception is raised by a query if only
    one object is expected, but multiple objects are returned. A base version
    of this exception is provided in :mod:`django.core.exceptions`; each model
    class contains a subclassed version that can be used to identify the
    specific object type that has returned multiple objects.

    See :meth:`~django.db.models.query.QuerySet.get()` for further information.

SuspiciousOperation
-------------------
.. exception:: SuspiciousOperation

    The :exc:`SuspiciousOperation` exception is raised when a user has
    performed an operation that should be considered suspicious from a security
    perspective, such as tampering with a session cookie. Subclasses of
    SuspiciousOperation include:

    * DisallowedHost
    * DisallowedModelAdminLookup
    * DisallowedRedirect
    * InvalidSessionKey
    * SuspiciousFileOperation
    * SuspiciousMultipartForm
    * SuspiciousSession
    * WizardViewCookieModified

    If a ``SuspiciousOperation`` exception reaches the WSGI handler level it is
    logged at the ``Error`` level and results in
    a :class:`~django.http.HttpResponseBadRequest`. See the :doc:`logging
    documentation </topics/logging/>` for more information.

PermissionDenied
----------------
.. exception:: PermissionDenied

    The :exc:`PermissionDenied` exception is raised when a user does not have
    permission to perform the action requested.

ViewDoesNotExist
----------------
.. exception:: ViewDoesNotExist

    The :exc:`ViewDoesNotExist` exception is raised by
    :mod:`django.core.urlresolvers` when a requested view does not exist.

MiddlewareNotUsed
-----------------
.. exception:: MiddlewareNotUsed

    The :exc:`MiddlewareNotUsed` exception is raised when a middleware is not
    used in the server configuration.

ImproperlyConfigured
--------------------
.. exception:: ImproperlyConfigured

    The :exc:`ImproperlyConfigured` exception is raised when Django is
    somehow improperly configured -- for example, if a value in ``settings.py``
    is incorrect or unparseable.

FieldError
----------
.. exception:: FieldError

    The :exc:`FieldError` exception is raised when there is a problem with a
    model field. This can happen for several reasons:

    - A field in a model clashes with a field of the same name from an
      abstract base class
    - An infinite loop is caused by ordering
    - A keyword cannot be parsed from the filter parameters
    - A field cannot be determined from a keyword in the query
      parameters
    - A join is not permitted on the specified field
    - A field name is invalid
    - A query contains invalid order_by arguments

ValidationError
---------------
.. exception:: ValidationError

    The :exc:`ValidationError` exception is raised when data fails form or
    model field validation. For more information about validation, see
    :doc:`Form and Field Validation </ref/forms/validation>`,
    :ref:`Model Field Validation <validating-objects>` and the
    :doc:`Validator Reference </ref/validators>`.

.. currentmodule:: django.core.urlresolvers

URL Resolver exceptions
=======================

URL Resolver exceptions are defined in :mod:`django.core.urlresolvers`.

Resolver404
--------------
.. exception:: Resolver404

    The :exc:`Resolver404` exception is raised by
    :func:`django.core.urlresolvers.resolve()` if the path passed to
    ``resolve()`` doesn't map to a view. It's a subclass of
    :class:`django.http.Http404`

NoReverseMatch
--------------
.. exception:: NoReverseMatch

    The :exc:`NoReverseMatch` exception is raised by
    :mod:`django.core.urlresolvers` when a matching URL in your URLconf
    cannot be identified based on the parameters supplied.

.. currentmodule:: django.db

Database Exceptions
===================

Database exceptions are provided in :mod:`django.db`.

Django wraps the standard database exceptions so that your Django code has a
guaranteed common implementation of these classes.

.. exception:: Error
.. exception:: InterfaceError
.. exception:: DatabaseError
.. exception:: DataError
.. exception:: OperationalError
.. exception:: IntegrityError
.. exception:: InternalError
.. exception:: ProgrammingError
.. exception:: NotSupportedError

The Django wrappers for database exceptions behave exactly the same as
the underlying database exceptions. See :pep:`249`, the Python Database API
Specification v2.0, for further information.

As per :pep:`3134`, a ``__cause__`` attribute is set with the original
(underlying) database exception, allowing access to any additional
information provided. (Note that this attribute is available under
both Python 2 and Python 3, although :pep:`3134` normally only applies
to Python 3.)

.. versionchanged:: 1.6

    Previous versions of Django only wrapped ``DatabaseError`` and
    ``IntegrityError``, and did not provide ``__cause__``.

.. exception:: models.ProtectedError

Raised to prevent deletion of referenced objects when using
:attr:`django.db.models.PROTECT`. :exc:`models.ProtectedError` is a subclass
of :exc:`IntegrityError`.

.. currentmodule:: django.http

Http Exceptions
===============

Http exceptions are provided in :mod:`django.http`.

.. exception:: UnreadablePostError

    The :exc:`UnreadablePostError` is raised when a user cancels an upload.

.. currentmodule:: django.db.transaction

Transaction Exceptions
======================

Transaction exceptions are defined in :mod:`django.db.transaction`.

.. exception:: TransactionManagementError

    The :exc:`TransactionManagementError` is raised for any and all problems
    related to database transactions.

Python Exceptions
=================

Django raises built-in Python exceptions when appropriate as well. See the
Python documentation for further information on the
built-in :mod:`exceptions`.

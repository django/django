The ``checksecure`` management command
======================================

The ``checksecure`` management command is a "linter" for simple improvements
you could make to your site's security configuration. It just runs a list of
check functions. Each check function can return a set of warnings, or the
empty set if it finds nothing to warn about.

.. contents:: :local:

When to run it
--------------

You can run it in your local development checkout. Your local dev settings
module may not be configured for SSL, so you may want to point it at a
different settings module, either by setting the ``DJANGO_SETTINGS_MODULE``
environment variable, or by passing the ``--settings`` option::

    django-admin.py checksecure --settings=production_settings

Or you could run it directly on a production or staging deployment to verify that the correct settings are in use.

You could even make it part of your integration test suite, if you want. The
:py:func:`djangosecure.check.run_checks` function runs all configured checks
and returns the complete set of warnings; you could write a simple test that
asserts that the returned value is empty.

.. _built-in-checks:

Built-in checks
---------------

The following check functions are built-in to django-secure, and will run by
default:

.. py:currentmodule:: djangosecure.check.djangosecure

.. py:function:: check_security_middleware

   Warns if :doc:`middleware` is not in your ``MIDDLEWARE_CLASSES``.

.. py:function:: check_sts

   Warns if :ref:`SECURE_HSTS_SECONDS` is not set to a non-zero value.

.. py:function:: check_sts_include_subdomains

   Warns if :ref:`SECURE_HSTS_INCLUDE_SUBDOMAINS` is not ``True``.

.. py:function:: check_frame_deny

   Warns if :ref:`SECURE_FRAME_DENY` is not ``True``.

.. py:function:: check_content_type_nosniff

   Warns if :ref:`SECURE_CONTENT_TYPE_NOSNIFF` is not ``True``.

.. py:function:: check_xss_filter

   Warns if :ref:`SECURE_BROWSER_XSS_FILTER` is not ``True``.

.. py:function:: check_ssl_redirect

   Warns if :ref:`SECURE_SSL_REDIRECT` is not ``True``.

.. py:function:: check_secret_key

   Warns if `SECRET_KEY`_ is empty, missing, or has a very low number of different characters.

.. _SECRET_KEY: http://docs.djangoproject.com/en/stable/ref/settings/#secret-key

.. py:currentmodule:: djangosecure.check.sessions

.. py:function:: check_session_cookie_secure

   Warns if you appear to be using Django's `session framework`_ and the
   `SESSION_COOKIE_SECURE`_ setting is not ``True``. This setting marks
   Django's session cookie as a secure cookie, which instructs browsers not to
   send it along with any insecure requests. Since it's trivial for a packet
   sniffer (e.g. `Firesheep`_) to hijack a user's session if the session cookie
   is sent unencrypted, there's really no good excuse not to have this on. (It
   will prevent you from using sessions on insecure requests; that's a good
   thing).

.. _Firesheep: http://codebutler.com/firesheep
.. _session framework: https://docs.djangoproject.com/en/stable/topics/http/sessions/
.. _SESSION_COOKIE_SECURE: https://docs.djangoproject.com/en/stable/topics/http/sessions/#session-cookie-secure

.. py:function:: check_session_cookie_httponly

   Warns if you appear to be using Django's `session framework`_ and the
   `SESSION_COOKIE_HTTPONLY`_ setting is not ``True``. This setting marks
   Django's session cookie as "HTTPOnly", meaning (in supporting browsers) its
   value can't be accessed from client-side scripts. Turning this on makes it
   less trivial for an attacker to escalate a cross-site scripting
   vulnerability into full hijacking of a user's session. There's not much
   excuse for leaving this off, either: if your code depends on reading session
   cookies from Javascript, you're probably doing it wrong.


.. _SESSION_COOKIE_HTTPONLY: https://docs.djangoproject.com/en/stable/topics/http/sessions/#session-cookie-httponly

.. py:currentmodule:: djangosecure.check.csrf

.. py:function:: check_csrf_middleware

   Warns if you do not have Django's built-in `CSRF protection`_ enabled
   globally via the `CSRF view middleware`_. It's important to CSRF protect any
   view that modifies server state; if you choose to do that piecemeal via the
   `csrf_protect`_ view decorator instead, just disable this check.

.. _CSRF protection: https://docs.djangoproject.com/en/stable/ref/contrib/csrf/
.. _CSRF view middleware: https://docs.djangoproject.com/en/stable/ref/contrib/csrf/#how-to-use-it
.. _csrf_protect: https://docs.djangoproject.com/en/stable/ref/contrib/csrf/#django.views.decorators.csrf.csrf_protect

Suggestions for additional built-in checks (or better, patches implementing
them) are welcome!


Modifying the list of check functions
-------------------------------------

By default, all of the :ref:`built-in checks <built-in-checks>` are run when
you run ``./manage.py checksecure``. However, some of these checks may not be
appropriate for your particular deployment configuration. For instance, if you
do your HTTP->HTTPS redirection in a loadbalancer, it'd be irritating for
``checksecure`` to constantly warn you about not having enabled
:ref:`SECURE_SSL_REDIRECT`. You can customize the list of checks by setting the
:ref:`SECURE_CHECKS` setting; you can just copy the default value and remove a
check or two; you can also write your own :ref:`custom checks <custom-checks>`.

.. _custom-checks:

Writing custom check functions
------------------------------

A ``checksecure`` check function can be any Python function that takes no
arguments and returns a Python iterable of warnings (an empty iterable if it
finds nothing to warn about).

Optionally, the function can have a ``messages`` attribute, which is a
dictionary mapping short warning codes returned by the function (which will be
displayed by ``checksecure`` if run with ``--verbosity=0``) to longer
explanations which will be displayed by ``checksecure`` when running at its
default verbosity level. For instance::

    from django.conf import settings

    def check_dont_let_the_bad_guys_in():
        if settings.LET_THE_BAD_GUYS_IN:
            return ["BAD_GUYS_LET_IN"]
        return []

    check_dont_let_the_bad_guys_in.messages = {
        "BAD_GUYS_LET_IN": (
            "Longer explanation of why it's a bad idea to let the bad guys in, "
            "and how to correct the situation.")
    }

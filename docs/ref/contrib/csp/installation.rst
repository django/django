.. _installation-chapter:

=============
Enabling  csp
=============

Edit your project's ``settings`` module. If you are not using the
built in report processor, all you need to do is::

    MIDDLEWARE_CLASSES = (
        # ...
        'django.contrib.csp.middleware.CSPMiddleware',
        # ...
    )

That should do it! Go on to :ref:`configuring CSP <configuration-chapter>`.

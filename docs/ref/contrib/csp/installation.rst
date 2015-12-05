.. _installation-chapter:

=====================
Installing django-csp
=====================

First, install django-csp via pip or from source::

    # pip
    $ pip install django-csp

::

    # source
    $ git clone https://github.com/mozilla/django-csp.git
    $ cd django-csp
    $ python setup.py install

Now edit your project's ``settings`` module. If you are not using the
built in report processor, all you need to do is::

    MIDDLEWARE_CLASSES = (
        # ...
        'csp.middleware.CSPMiddleware',
        # ...
    )

That should do it! Go on to :ref:`configuring CSP <configuration-chapter>`.

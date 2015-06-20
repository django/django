Installation
============

Channels is available on PyPI - to install it, just run::

    pip install -U channels

Once that's done, you should add ``channels`` to your
``INSTALLED_APPS`` setting::

    INSTALLED_APPS = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
        ...
        'channels',
    )

That's it! Once enabled, ``channels`` will integrate itself into Django and
take control of the ``runserver`` command. See :doc:`getting-started` for more.

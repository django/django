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

Then, make a default routing in ``myproject/routing.py``::

    from channels.routing import ProtocolTypeRouter

    application = ProtocolTypeRouter({
        # Empty for now (http->django views is added by default)
    })

And finally, set your ``ASGI_APPLICATION`` setting to point to that routing
object as your root application::

    ASGI_APPLICATION = "myproject.routing.application"

That's it! Once enabled, ``channels`` will integrate itself into Django and
take control of the ``runserver`` command. See :doc:`introduction` for more.

.. note::
  Please be wary of any other third-party apps that require an overloaded or
  replacement ``runserver`` command. Channels provides a separate
  ``runserver`` command and may conflict with it. An example
  of such a conflict is with `whitenoise.runserver_nostatic <https://github.com/evansd/whitenoise/issues/77>`_
  from `whitenoise <https://github.com/evansd/whitenoise>`_. In order to
  solve such issues, try moving ``channels`` to the top of your ``INSTALLED_APPS``
  or remove the offending app altogether.


Installing the latest development version
-----------------------------------------

To install the latest version of Channels, clone the repo, change to the repo,
change to the repo directory, and pip install it into your current virtual
environment::

    $ git clone git@github.com:django/channels.git
    $ cd channels
    $ <activate your project’s virtual environment>
    (environment) $ pip install -e .  # the dot specifies the current repo

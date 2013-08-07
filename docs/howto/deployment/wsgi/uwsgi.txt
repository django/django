============================
How to use Django with uWSGI
============================

.. highlight:: bash

uWSGI_ is a fast, self-healing and developer/sysadmin-friendly application
container server coded in pure C.

.. _uWSGI: http://projects.unbit.it/uwsgi/

.. seealso::

    The uWSGI docs offer a `tutorial`_ covering Django, nginx, and uWSGI (one
    possible deployment setup of many). The docs below are focused on how to
    integrate Django with uWSGI.

    .. _tutorial: https://uwsgi.readthedocs.org/en/latest/tutorials/Django_and_nginx.html

Prerequisite: uWSGI
===================

The uWSGI wiki describes several `installation procedures`_. Using pip, the
Python package manager, you can install any uWSGI version with a single
command. For example:

.. code-block:: bash

    # Install current stable version.
    $ sudo pip install uwsgi

    # Or install LTS (long term support).
    $ sudo pip install http://projects.unbit.it/downloads/uwsgi-lts.tar.gz

.. _installation procedures: http://projects.unbit.it/uwsgi/wiki/Install

.. warning::

    Some distributions, including Debian and Ubuntu, ship an outdated version
    of uWSGI that does not conform to the WSGI specification. Versions prior to
    1.2.6 do not call ``close`` on the response object after handling a
    request. In those cases the :data:`~django.core.signals.request_finished`
    signal isn't sent. This can result in idle connections to database and
    memcache servers.

uWSGI model
-----------

uWSGI operates on a client-server model. Your Web server (e.g., nginx, Apache)
communicates with a django-uwsgi "worker" process to serve dynamic content.
See uWSGI's `background documentation`_ for more detail.

.. _background documentation: http://projects.unbit.it/uwsgi/wiki/Background

Configuring and starting the uWSGI server for Django
----------------------------------------------------

uWSGI supports multiple ways to configure the process. See uWSGI's
`configuration documentation`_ and `examples`_

.. _configuration documentation: http://projects.unbit.it/uwsgi/wiki/Doc
.. _examples: http://projects.unbit.it/uwsgi/wiki/Example

Here's an example command to start a uWSGI server::

    uwsgi --chdir=/path/to/your/project \
        --module=mysite.wsgi:application \
        --env DJANGO_SETTINGS_MODULE=mysite.settings \
        --master --pidfile=/tmp/project-master.pid \
        --socket=127.0.0.1:49152 \      # can also be a file
        --processes=5 \                 # number of worker processes
        --uid=1000 --gid=2000 \         # if root, uwsgi can drop privileges
        --harakiri=20 \                 # respawn processes taking more than 20 seconds
        --max-requests=5000 \           # respawn processes after serving 5000 requests
        --vacuum \                      # clear environment on exit
        --home=/path/to/virtual/env \   # optional path to a virtualenv
        --daemonize=/var/log/uwsgi/yourproject.log      # background the process

This assumes you have a top-level project package named ``mysite``, and
within it a module :file:`mysite/wsgi.py` that contains a WSGI ``application``
object. This is the layout you'll have if you ran ``django-admin.py
startproject mysite`` (using your own project name in place of ``mysite``) with
a recent version of Django. If this file doesn't exist, you'll need to create
it. See the :doc:`/howto/deployment/wsgi/index` documentation for the default
contents you should put in this file and what else you can add to it.

The Django-specific options here are:

* ``chdir``: The path to the directory that needs to be on Python's import
  path -- i.e., the directory containing the ``mysite`` package.
* ``module``: The WSGI module to use -- probably the ``mysite.wsgi`` module
  that :djadmin:`startproject` creates.
* ``env``: Should probably contain at least ``DJANGO_SETTINGS_MODULE``.
* ``home``: Optional path to your project virtualenv.

Example ini configuration file::

    [uwsgi]
    chdir=/path/to/your/project
    module=mysite.wsgi:application
    master=True
    pidfile=/tmp/project-master.pid
    vacuum=True
    max-requests=5000
    daemonize=/var/log/uwsgi/yourproject.log

Example ini configuration file usage::

    uwsgi --ini uwsgi.ini

See the uWSGI docs on `managing the uWSGI process`_ for information on
starting, stopping and reloading the uWSGI workers.

.. _managing the uWSGI process: http://projects.unbit.it/uwsgi/wiki/Management

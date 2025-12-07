================================
How to use Django with Hypercorn
================================

Hypercorn_ is an ASGI server that supports HTTP/1, HTTP/2, and HTTP/3
with an emphasis on protocol support.

Installing Hypercorn
====================

You can install Hypercorn with ``pip``:

.. code-block:: shell

    python -m pip install hypercorn

Running Django in Hypercorn
===========================

When :pypi:`Hypercorn` is installed, a ``hypercorn`` command is available
which runs ASGI applications. Hypercorn needs to be called with the
location of a module containing an ASGI application object, followed
by what the application is called (separated by a colon).

For a typical Django project, invoking Hypercorn would look like:

.. code-block:: shell

    hypercorn myproject.asgi:application

This will start one process listening on ``127.0.0.1:8000``. It
requires that your project be on the Python path; to ensure that run
this command from the same directory as your ``manage.py`` file.

For more advanced usage, please read the `Hypercorn documentation
<Hypercorn_>`_.

.. _Hypercorn: https://hypercorn.readthedocs.io/

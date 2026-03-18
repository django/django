==============================
How to use Django with Granian
==============================

Granian_ is a Rust-based high-performance HTTP server for Python applications,
supporting ASGI and WSGI interfaces.

.. _Granian: https://github.com/emmett-framework/granian

Installing Granian
==================

You can install Granian with ``pip``:

.. code-block:: shell

    python -m pip install granian

Running Django in Granian
=========================

When Granian is installed, a ``granian`` command is available which runs WSGI
applications. Granian needs to be called with the location of a module
containing a WSGI application object named ``application``, using the
``--interface wsgi`` option.

For a typical Django project, invoking Granian would look like:

.. code-block:: shell

    granian myproject.wsgi:application --interface wsgi

This will start one process listening on ``127.0.0.1:8000``. It requires that
your project be on the Python path; to ensure that, run this command from the
same directory as your ``manage.py`` file.

For more advanced usage, please read the `Granian documentation <Granian_>`_.

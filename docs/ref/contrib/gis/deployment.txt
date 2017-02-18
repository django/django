===================
Deploying GeoDjango
===================

Basically, the deployment of a GeoDjango application is not different from
the deployment of a normal Django application. Please consult Django's
:doc:`deployment documentation </howto/deployment/index>`.

.. warning::

    GeoDjango uses the GDAL geospatial library which is
    not thread safe at this time.  Thus, it is *highly* recommended
    to not use threading when deploying -- in other words, use an
    appropriate configuration of Apache.

    For example, when configuring your application with ``mod_wsgi``,
    set the ``WSGIDaemonProcess`` attribute ``threads`` to ``1``, unless
    Apache may crash when running your GeoDjango application.  Increase the
    number of ``processes`` instead.

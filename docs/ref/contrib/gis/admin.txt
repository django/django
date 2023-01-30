======================
GeoDjango's admin site
======================

.. module:: django.contrib.gis.admin
    :synopsis: GeoDjango's extensions to the admin site.

``GISModelAdmin``
=================

.. class:: GISModelAdmin

    .. attribute:: gis_widget

        The widget class to be used for
        :class:`~django.contrib.gis.db.models.GeometryField`. Defaults to
        :class:`~django.contrib.gis.forms.widgets.OSMWidget`.

    .. attribute:: gis_widget_kwargs

        The keyword arguments that would be passed to the :attr:`gis_widget`.
        Defaults to an empty dictionary.

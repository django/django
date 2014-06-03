=====================
Model class reference
=====================

.. currentmodule:: django.db.models

This document covers features of the :class:`~django.db.models.Model` class.
For more information about models, see :doc:`the complete list of Model
reference guides </ref/models/index>`.

Attributes
==========

``objects``
-----------

.. attribute:: Model.objects

    Each non-abstract :class:`~django.db.models.Model` class must have a
    :class:`~django.db.models.Manager` instance added to it.
    Django ensures that in your model class you have  at least a
    default ``Manager`` specified. If you don't add your own ``Manager``,
    Django will add an attribute ``objects`` containing default
    :class:`~django.db.models.Manager` instance. If you add your own
    :class:`~django.db.models.Manager` instance attribute, the default one does
    not appear. Consider the following example::

        from django.db import models

        class Person(models.Model):
            # Add manager with another name
            people = models.Manager()

    For more details on model managers see :doc:`Managers </topics/db/managers>`
    and :ref:`Retrieving objects <retrieving-objects>`.

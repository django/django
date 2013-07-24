# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.core import checks
from django.db import models
from django.db.models.fields import FieldDoesNotExist


class CurrentSiteManager(models.Manager):
    "Use this to limit objects to those associated with the current site."

    def __init__(self, field_name=None):
        super(CurrentSiteManager, self).__init__()
        self.__field_name = field_name

    def _get_field_name(self):
        """ Return self.__field_name or 'site' or 'sites'. """

        if not self.__field_name:
            try:
                self.model._meta.get_field('site')
            except FieldDoesNotExist:
                self.__field_name = 'sites'
            else:
                self.__field_name = 'site'
        return self.__field_name

    def get_queryset(self):
        return super(CurrentSiteManager, self).get_queryset().filter(
            **{self._get_field_name() + '__id__exact': settings.SITE_ID})

    def check(self, **kwargs):
        errors = super(CurrentSiteManager, self).check(**kwargs)
        errors.extend(self._check_field_name())
        return errors

    def _check_field_name(self):
        field_name = self._get_field_name()
        try:
            field = self.model._meta.get_field(field_name)
        except FieldDoesNotExist:
            return [checks.Error(
                'No field %s.%s.\n'
                'CurrentSiteManager needs a field named "%s".'
                % (self.model._meta.object_name, field_name, field_name),
                hint='Ensure that you did not misspell the field name. '
                'Does the field exist?',
                obj=self)]

        if not isinstance(field, (models.ForeignKey, models.ManyToManyField)):
            return [checks.Error(
                'CurrentSiteManager uses a non-relative field.\n'
                '%s.%s should be a ForeignKey or ManyToManyField.'
                % (self.model._meta.object_name, field_name),
                hint=None, obj=self)]

        return []
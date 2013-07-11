# -*- coding: utf8 -*-
from __future__ import unicode_literals

from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class BaseCheckError(object):
    def __init__(self, msg, hint, obj=None):
        self.msg = msg
        self.hint = hint
        self.obj = obj

    def __eq__(self, other):
        return all(getattr(self, attr) == getattr(other, attr)
            for attr in ['msg', 'hint', 'obj'])

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        from django.db import models
        from django.db.models.fields import Field

        result = ""
        if isinstance(self.obj, Field):
            model = self.obj.model
            app = model._meta.app_label
            result += '%s.%s.%s: ' \
                % (app, model._meta.object_name, self.obj.name)
        elif isinstance(self.obj, models.base.ModelBase):
            model = self.obj
            app = model._meta.app_label
            result += '%s.%s: ' % (app, model._meta.object_name)
        else:
            result += '?: '
        result += self.msg
        if self.hint:
            result += "\nHINT: %s" % self.hint
        return result

    def __repr__(self):
        return "<%s: msg=%r, hint=%r, obj=%r>" % \
            (self.__class__.__name__, self.msg, self.hint, self.obj)


class Error(BaseCheckError):
    pass


class Warning(BaseCheckError):
    pass

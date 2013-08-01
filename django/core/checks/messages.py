# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.encoding import python_2_unicode_compatible, force_str


# Levels
DEBUG = 10
INFO = 20
WARNING = 30
ERROR = 40
CRITICAL = 50


@python_2_unicode_compatible
class CheckMessage(object):
    def __init__(self, level, msg, hint, obj=None):
        assert isinstance(level, int), "The first argument should be level."
        self.level = level
        self.msg = msg
        self.hint = hint
        self.obj = obj

    def __eq__(self, other):
        return all(getattr(self, attr) == getattr(other, attr)
                   for attr in ['level', 'msg', 'hint', 'obj'])

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        from django.db import models

        if self.obj is None:
            obj = "?"
        elif isinstance(self.obj, models.base.ModelBase):
            # We need to hardcode ModelBase and Field cases because its __str__
            # method doesn't return "applabel.modellabel" and cannot be changed.
            model = self.obj
            app = model._meta.app_label
            obj = '%s.%s' % (app, model._meta.object_name)
        else:
            obj = force_str(self.obj)
        hint = "\n\tHINT: %s" % self.hint if self.hint else ''
        return "%s: %s%s" % (obj, self.msg, hint)

    def __repr__(self):
        return "<%s: level=%r, msg=%r, hint=%r, obj=%r>" % \
            (self.__class__.__name__, self.level, self.msg, self.hint, self.obj)


class ConcreteCheckMessage(CheckMessage):
    def __init__(self, *args, **kwargs):
        # At this moment self.level is a class attribute defined in derivatives.
        super(ConcreteCheckMessage, self).__init__(self.level, *args, **kwargs)


class Debug(ConcreteCheckMessage):
    level = DEBUG


class Info(ConcreteCheckMessage):
    level = INFO


class Warning(ConcreteCheckMessage):
    level = WARNING


class Error(ConcreteCheckMessage):
    level = ERROR


class Critical(ConcreteCheckMessage):
    level = CRITICAL

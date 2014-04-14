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

    def __init__(self, level, msg, hint=None, obj=None, id=None):
        assert isinstance(level, int), "The first argument should be level."
        self.level = level
        self.msg = msg
        self.hint = hint
        self.obj = obj
        self.id = id

    def __eq__(self, other):
        return all(getattr(self, attr) == getattr(other, attr)
                   for attr in ['level', 'msg', 'hint', 'obj', 'id'])

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
        id = "(%s) " % self.id if self.id else ""
        hint = "\n\tHINT: %s" % self.hint if self.hint else ''
        return "%s: %s%s%s" % (obj, id, self.msg, hint)

    def __repr__(self):
        return "<%s: level=%r, msg=%r, hint=%r, obj=%r, id=%r>" % \
            (self.__class__.__name__, self.level, self.msg, self.hint, self.obj, self.id)

    def is_serious(self):
        return self.level >= ERROR

    def is_silenced(self):
        from django.conf import settings
        return self.id in settings.SILENCED_SYSTEM_CHECKS


class Debug(CheckMessage):
    def __init__(self, *args, **kwargs):
        return super(Debug, self).__init__(DEBUG, *args, **kwargs)


class Info(CheckMessage):
    def __init__(self, *args, **kwargs):
        return super(Info, self).__init__(INFO, *args, **kwargs)


class Warning(CheckMessage):
    def __init__(self, *args, **kwargs):
        return super(Warning, self).__init__(WARNING, *args, **kwargs)


class Error(CheckMessage):
    def __init__(self, *args, **kwargs):
        return super(Error, self).__init__(ERROR, *args, **kwargs)


class Critical(CheckMessage):
    def __init__(self, *args, **kwargs):
        return super(Critical, self).__init__(CRITICAL, *args, **kwargs)

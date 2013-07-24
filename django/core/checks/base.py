# -*- coding: utf8 -*-
from __future__ import unicode_literals

from django.utils.encoding import python_2_unicode_compatible
from django.utils.itercompat import is_iterable


@python_2_unicode_compatible
class BaseCheckMessage(object):
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
        elif isinstance(self.obj, models.Manager):
            model = self.obj.model
            model_name = model._meta.object_name
            opts = model._meta
            app = model._meta.app_label
            manager_name = next(name for (_, name, manager)
                in opts.concrete_managers + opts.abstract_managers
                if manager == self.obj)
            result += '%s.%s.%s: ' % (app, model_name, manager_name)
        else:
            result += '?: '
        result += self.msg
        if self.hint:
            result += "\nHINT: %s" % self.hint
        return result

    def __repr__(self):
        return "<%s: msg=%r, hint=%r, obj=%r>" % \
            (self.__class__.__name__, self.msg, self.hint, self.obj)


class Error(BaseCheckMessage):
    pass


class Warning(BaseCheckMessage):
    pass


class CheckingFramework(object):

    def __init__(self):
        self.registered_checks = []

    def register(self, f):
        """
        Register given function. It will be called during `run_checks`. The
        function should receive **kwargs and return list of Errors and
        Warnings.
        """
        self.registered_checks.append(f)

    def run_checks(self):
        """ Run all registered checks and return list of Errors and Warnings.
        """
        errors = []
        for f in self.registered_checks:
            new_errors = f()
            assert is_iterable(new_errors), (
                "The function %r did not return a list. All functions registered "
                "in checking framework must return a list." % f)
            errors.extend(new_errors)
        return errors


framework = CheckingFramework()
register = framework.register
run_checks = framework.run_checks


###############################################################################
# Checks registered by default
###############################################################################

def check_all_models(**kwargs):
    from django.db import models

    errors = []
    for cls in models.get_models(include_swapped=True):
        errors.extend(cls.check())
    return errors


register(check_all_models)

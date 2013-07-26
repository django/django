# -*- coding: utf8 -*-
from __future__ import unicode_literals

from django.utils.encoding import python_2_unicode_compatible, force_str
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

        if self.obj is None:
            obj = "?"
        elif isinstance(self.obj, models.base.ModelBase):
            # We need to hardcode ModelBase case because its __repr__ method
            # doesn't return "applabel.modellabel" and cannot be changed.
            model = self.obj
            app = model._meta.app_label
            obj = '%s.%s' % (app, model._meta.object_name)
        else:
            obj = force_str(self.obj)
        hint = " HINT: %s" % self.hint if self.hint else ''
        return "%s: %s%s" % (obj, self.msg, hint)

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

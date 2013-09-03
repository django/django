# -*- encoding: utf-8 -*-
from __future__ import unicode_literals


class BaseValidator(object):
    def validate(self, cls, model):
        pass


class ModelAdminValidator(BaseValidator):
    pass


class InlineValidator(BaseValidator):
    pass

# -*- encoding: utf-8 -*-
from __future__ import unicode_literals


class BaseValidator(object):
    def validate(self, cls, model):
        for m in dir(self):
            if m.startswith('validate_'):
                getattr(self, m)(cls, model)


class ModelAdminValidator(BaseValidator):
    pass


class InlineValidator(BaseValidator):
    pass

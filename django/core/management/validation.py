import sys

from django.core.management.color import color_style
from django.utils.encoding import force_str


class ModelErrorCollection:
    def __init__(self, outfile=sys.stdout):
        self.errors = 0
        self.outfile = outfile
        self.style = color_style()

    def add(self, msg):
        self.errors += 1
        self.outfile.write(self.style.ERROR(force_str(msg)))


def get_validation_errors(outfile, app=None):
    """
    Validates all models that are part of the specified app. If no app name is
    provided, validates all models of all installed apps. Writes errors, if any,
    to outfile. Returns number of errors.
    """
    from django.db import models
    from django.db.models.loading import get_app_errors

    e = ModelErrorCollection(outfile)
    all_errors = []

    for (app_name, error) in get_app_errors().items():
        e.add(app_name, error)

    # Trigger checking framework for each model
    for cls in models.get_models(app, include_swapped=True):
        errors = cls.check()
        for error in errors:
            msg = error.msg
            if error.hint:
                msg += '\n%s' % error.hint
            e.add(msg)
        all_errors.extend(errors)

    return all_errors

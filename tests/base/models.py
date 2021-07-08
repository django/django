from django.db import models

# The models definitions below used to crash. Generating models dynamically
# at runtime is a bad idea because it pollutes the app registry. This doesn't
# integrate well with the test suite but at least it prevents regressions.


class CustomBaseModel(models.base.ModelBase):
    pass


class MyModel(models.Model, metaclass=CustomBaseModel):
    """Model subclass with a custom base using metaclass."""

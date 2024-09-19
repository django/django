from django.db import models


class CustomBaseModel(models.base.ModelBase):
    pass


class MyModel(models.Model, metaclass=CustomBaseModel):
    pass


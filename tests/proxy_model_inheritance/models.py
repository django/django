
from django.db import models


class ConcreteModel(models.Model):
    pass


class ConcreteModelSubclass(ConcreteModel):
    pass


class ConcreteModelSubclassProxy(ConcreteModelSubclass):
    class Meta:
        proxy = True

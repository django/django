from django.db import models


class ConcreteModel(models.Model):
    pass


class ProxyModel(ConcreteModel):
    class Meta:
        proxy = True


class ConcreteModelSubclass(ProxyModel):
    pass


class ConcreteModelSubclassProxy(ConcreteModelSubclass):
    class Meta:
        proxy = True

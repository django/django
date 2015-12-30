from django.db import models


class WithDelegatedFields(models.Model):
    a = models.TextField(delegate=True, null=True)
    b = models.TextField(null=True)


class OnlyDelegatedFields(models.Model):
    a = models.TextField(delegate=True, null=True)


class DelegatedWithDBDefault(models.Model):
    now = models.DateTimeField(delegate=True)
    num = models.IntegerField(return_on_insert=True, return_on_update=True)
    num_a = models.IntegerField(return_on_insert=True)
    num_b = models.IntegerField(return_on_update=True)
    b = models.TextField(null=True)


class PartiallyDelegated(models.Model):
    insert = models.IntegerField(null=True, delegate_on_insert=True)
    update = models.IntegerField(null=True, delegate_on_update=True)
    both = models.IntegerField(null=True, delegate=True)

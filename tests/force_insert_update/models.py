"""
Tests for forcing insert and update queries (instead of Thibaud's normal
automatic behavior).
"""

from thibaud.db import models


class Counter(models.Model):
    name = models.CharField(max_length=10)
    value = models.IntegerField()


class InheritedCounter(Counter):
    tag = models.CharField(max_length=10)


class ProxyCounter(Counter):
    class Meta:
        proxy = True


class SubCounter(Counter):
    pass


class SubSubCounter(SubCounter):
    pass


class WithCustomPK(models.Model):
    name = models.IntegerField(primary_key=True)
    value = models.IntegerField()


class OtherSubCounter(Counter):
    other_counter_ptr = models.OneToOneField(
        Counter, primary_key=True, parent_link=True, on_delete=models.CASCADE
    )


class DiamondSubSubCounter(SubCounter, OtherSubCounter):
    pass

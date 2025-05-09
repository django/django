import typing

from django.db import models

T = typing.TypeVar("T")


class GenericModel(typing.Generic[T], models.Model):
    """A model inheriting from typing.Generic"""


class GenericModel312[T](models.Model):
    """A model inheriting from typing.Generic via the 3.12 syntax"""


T1 = typing.TypeVar("T1")
T2 = typing.TypeVar("T2")
T3 = typing.TypeVar("T3")


class Parent1(typing.Generic[T1, T2]):
    pass


class Parent2(typing.Generic[T1, T2]):
    pass


class Child(Parent1[T1, T3], Parent2[T2, T3]):
    pass


class CustomGenericModel(Child[T1, T3, T2], models.Model):
    """A model inheriting from a custom subclass of typing.Generic"""

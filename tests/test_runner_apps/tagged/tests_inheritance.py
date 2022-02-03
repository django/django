from unittest import TestCase

from django.test import tag


@tag("foo")
class FooBase(TestCase):
    pass


class Foo(FooBase):
    def test_no_new_tags(self):
        pass

    @tag("baz")
    def test_new_func_tag(self):
        pass


@tag("bar")
class FooBar(FooBase):
    def test_new_class_tag_only(self):
        pass

    @tag("baz")
    def test_new_class_and_func_tags(self):
        pass

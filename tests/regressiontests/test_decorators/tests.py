"""
>>> from django.test import SkippedTest
>>> from django.test.decorators import *

>>> skip_test()(None)(None)
Traceback (most recent call last):
    ...
SkippedTest

>>> skip_test(reason='testing')(None)(None)
Traceback (most recent call last):
    ...
SkippedTest: testing

>>> conditional_skip(lambda: False)(None)(None)
Traceback (most recent call last):
    ...
SkippedTest

>>> conditional_skip(lambda: True)(lambda: True)()
True

"""

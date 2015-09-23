from __future__ import unicode_literals

import pickle

from django.contrib.auth.models import User
from django.db import models
from django.test import TestCase
from django.utils import six
from django.utils.functional import SimpleLazyObject


class UserProfile(models.Model):
    user = models.OneToOneField(User, models.CASCADE, related_name='profile')
    dummy = models.BooleanField(default=True)


class TestUtilsSimpleLazyObjectDjangoTestCase(TestCase):

    def test_pickle_py2_regression(self):
        # See ticket #20212
        user = User.objects.create_user('johndoe', 'john@example.com', 'pass')
        x = SimpleLazyObject(lambda: user)

        # This would fail with "TypeError: can't pickle instancemethod objects",
        # only on Python 2.X.
        pickle.dumps(x)

        # Try the variant protocol levels.
        pickle.dumps(x, 0)
        pickle.dumps(x, 1)
        pickle.dumps(x, 2)

        if six.PY2:
            import cPickle

            # This would fail with "TypeError: expected string or Unicode object, NoneType found".
            cPickle.dumps(x)

    def test_pickle_model_instance_with_one_to_one_field(self):

        # See ticket #25426
        user = User.objects.create_user('johndoe', 'john@example.com', 'pass')
        UserProfile.objects.create(user=user)

        x = SimpleLazyObject(lambda: user)
        x.profile  # accsss related object

        # This would fail with "RuntimeError: dictionary changed size during iteration",
        # on django 1.8 both on python3.x and 2.x
        pickle.dumps(x)  # Fails

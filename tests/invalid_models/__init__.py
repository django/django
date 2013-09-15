# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models.loading import cache
from django.test import TestCase


class IsolatedModelsTestCase(TestCase):

    def setUp(self):
        # If you create a model in a test, the model is accessible in other
        # tests. To avoid this, we need to clear list of all models created in
        # `invalid_models` module.
        cache.app_models['invalid_models'] = {}
        cache._get_models_cache = {}

    tearDown = setUp

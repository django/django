from django.db.models.base import ModelState, ModelStateCacheDescriptor
from django.test import SimpleTestCase


class ModelStateTests(SimpleTestCase):

    def test_fields_cache_descriptor(self):
        self.assertIsInstance(ModelState.fields_cache, ModelStateCacheDescriptor)

    def test_related_managers_descriptor(self):
        self.assertIsInstance(ModelState.related_managers_cache, ModelStateCacheDescriptor)

"""
Test for model_to_dict with empty fields list.
"""
from django.test import SimpleTestCase
from django.db import models
from django.forms.models import model_to_dict


class TestModel(models.Model):
    name = models.CharField(max_length=100)
    value = models.IntegerField(default=0)
    
    class Meta:
        app_label = 'test_app'


class ModelToDictTests(SimpleTestCase):
    def test_model_to_dict_empty_fields_list(self):
        """model_to_dict with empty fields list should return empty dict."""
        instance = TestModel(name='test', value=42)
        result = model_to_dict(instance, fields=[])
        self.assertEqual(result, {})
    
    def test_model_to_dict_no_fields_param(self):
        """model_to_dict without fields param should return all fields."""
        instance = TestModel(name='test', value=42)
        result = model_to_dict(instance)
        self.assertIn('name', result)
        self.assertIn('value', result)
    
    def test_model_to_dict_specific_fields(self):
        """model_to_dict with specific fields should return only those fields."""
        instance = TestModel(name='test', value=42)
        result = model_to_dict(instance, fields=['name'])
        self.assertIn('name', result)
        self.assertNotIn('value', result)

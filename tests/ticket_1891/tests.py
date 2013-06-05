from __future__ import absolute_import

from django.forms import ModelForm
from django.forms.models import ModelChoiceField
from django.test import TestCase

from .models import Group, Asset, Proxy

# Create your tests here.
class ForeignKeyDistinctTest(TestCase):
    longMessage = True

    def test_distinct_list(self):
        socks  = Group.objects.create(name="Socks Proxy")
        web    = Group.objects.create(name="Web Proxy")
        asset = Asset.objects.create(name="Asset 1")
        asset.groups = [socks, web]
        asset.save()

        proxy = Proxy()
        asset_field = proxy._meta.get_field('asset')
        # import pdb; pdb.set_trace()
        actual_choices = asset_field.rel.to._default_manager.complex_filter(asset_field.rel.limit_choices_to).distinct()
        self.assertEqual([asset], list(actual_choices),
            "There is only one asset to choose from, so it should only "
            "be returned once")
        
        class ProxyForm(ModelForm):
            class Meta:
                model = Proxy

        form = ProxyForm()
        asset_field = form.base_fields['asset']
        self.assertIsInstance(asset_field, ModelChoiceField)

        expected_choices = [
            ("", asset_field.empty_label),
            (asset.id, asset.name),
        ]

        self.assertEqual(expected_choices, list(asset_field.choices),
            "There is only one asset to choose from, so it should only "
            "be displayed once")

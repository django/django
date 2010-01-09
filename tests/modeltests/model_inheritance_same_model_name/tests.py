from django.test import TestCase
from modeltests.model_inheritance.models import Title

class InheritanceSameModelNameTests(TestCase):

    def setUp(self):
        # The Title model has distinct accessors for both
        # model_inheritance.Copy and model_inheritance_same_model_name.Copy
        # models.
        self.title = Title.objects.create(title='Lorem Ipsum')

    def test_inheritance_related_name(self):
        from modeltests.model_inheritance.models import Copy
        self.assertEquals(
            self.title.attached_model_inheritance_copy_set.create(
                content='Save $ on V1agr@',
                url='http://v1agra.com/',
                title='V1agra is spam',
            ), Copy.objects.get(content='Save $ on V1agr@'))

    def test_inheritance_with_same_model_name(self):
        from modeltests.model_inheritance_same_model_name.models import Copy
        self.assertEquals(
            self.title.attached_model_inheritance_same_model_name_copy_set.create(
                content='The Web framework for perfectionists with deadlines.',
                url='http://www.djangoproject.com/',
                title='Django Rocks'
            ), Copy.objects.get(content='The Web framework for perfectionists with deadlines.'))

    def test_related_name_attribute_exists(self):
        # The Post model doesn't have an attribute called 'attached_%(app_label)s_%(class)s_set'.
        self.assertEqual(hasattr(self.title, 'attached_%(app_label)s_%(class)s_set'), False)

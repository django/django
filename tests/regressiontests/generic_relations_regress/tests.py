from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from models import Link, Place, Restaurant

class GenericRelationTests(TestCase):
    
    def test_inherited_models_content_type(self):
        """
        Test that GenericRelations on inherited classes use the correct content
        type.
        """
        
        p = Place.objects.create(name="South Park")
        r = Restaurant.objects.create(name="Chubby's")        
        l1 = Link.objects.create(content_object=p)
        l2 = Link.objects.create(content_object=r)
        self.assertEqual(list(p.links.all()), [l1])
        self.assertEqual(list(r.links.all()), [l2])
        
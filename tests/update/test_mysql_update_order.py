"""
Regression test for Django Ticket #36877
Tests that UPDATE operations with F() expressions behave atomically on MySQL.
"""
from django.db import models
from django.db.models import F
from django.db.models.functions import Length
from django.test import TestCase


class Entity(models.Model):
    """Test model with a field that derives from another"""
    name = models.CharField(max_length=100)
    name_length = models.PositiveSmallIntegerField(default=0)

    class Meta:
        app_label = 'update'


class MySQLUpdateOrderTest(TestCase):
    """
    Test that UPDATE assignments are evaluated atomically using original values,
    not sequentially (MySQL-specific issue).
    """
    
    def test_update_with_f_expression_uses_original_value(self):
        """
        When updating multiple fields where one uses an F() expression
        referencing another field being updated, the F() expression should
        use the ORIGINAL value, not the new value.
        
        This tests the example from Ticket #36877.
        """
        # Create entity with name="Bob" (length 3)
        entity = Entity.objects.create(name="Bob", name_length=3)
        
        # Update name to "Alice" and name_length to Length("name")
        Entity.objects.filter(pk=entity.pk).update(
            name="Alice",
            name_length=Length("name")
        )
        
        entity.refresh_from_db()
        
        # On MySQL (buggy), this will likely be 5 instead of 3
        if entity.name_length == 5:
            print("✗ [CONFIRMED] Bug reproduced: name_length is 5 (new value) instead of 3 (old value)")
        elif entity.name_length == 3:
            print("✓ PASS: name_length is 3 (correct - used original value)")
        
        self.assertEqual(entity.name, "Alice")
        self.assertEqual(entity.name_length, 3, 
            f"Expected name_length=3, but got {entity.name_length}. This confirms the non-atomic update bug.")

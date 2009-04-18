from django import db
from django import forms
from django.conf import settings
from django.test import TestCase
from models import Person, Triple, FilePathModel

class ModelMultipleChoiceFieldTests(TestCase):
    
    def setUp(self):
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
        
    def tearDown(self):
        settings.DEBUG = self.old_debug
    
    def test_model_multiple_choice_number_of_queries(self):
        """
        Test that ModelMultipleChoiceField does O(1) queries instead of
        O(n) (#10156).
        """
        for i in range(30):
            Person.objects.create(name="Person %s" % i)
        
        db.reset_queries()
        f = forms.ModelMultipleChoiceField(queryset=Person.objects.all())
        selected = f.clean([1, 3, 5, 7, 9])
        self.assertEquals(len(db.connection.queries), 1)        

class TripleForm(forms.ModelForm):
    class Meta:
        model = Triple

class UniqueTogetherTests(TestCase):
    def test_multiple_field_unique_together(self):
        """
        When the same field is involved in multiple unique_together
        constraints, we need to make sure we don't remove the data for it
        before doing all the validation checking (not just failing after
        the first one).
        """
        Triple.objects.create(left=1, middle=2, right=3)

        form = TripleForm({'left': '1', 'middle': '2', 'right': '3'})
        self.failIf(form.is_valid())

        form = TripleForm({'left': '1', 'middle': '3', 'right': '1'})
        self.failUnless(form.is_valid())

class FPForm(forms.ModelForm):
    class Meta:
        model = FilePathModel

class FilePathFieldTests(TestCase):
    def test_file_path_field_blank(self):
        """
        Regression test for #8842: FilePathField(blank=True)
        """
        form = FPForm()
        names = [p[1] for p in form['path'].field.choices]
        names.sort()
        self.assertEqual(names, ['---------', '__init__.py', 'models.py', 'tests.py'])

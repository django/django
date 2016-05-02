from django.test import TestCase

from .models import Document


class FileFieldTests(TestCase):

    def test_clearable(self):
        """
        FileField.save_form_data() will clear its instance attribute value if
        passed False.
        """
        d = Document(myfile='something.txt')
        self.assertEqual(d.myfile, 'something.txt')
        field = d._meta.get_field('myfile')
        field.save_form_data(d, False)
        self.assertEqual(d.myfile, '')

    def test_unchanged(self):
        """
        FileField.save_form_data() considers None to mean "no change" rather
        than "clear".
        """
        d = Document(myfile='something.txt')
        self.assertEqual(d.myfile, 'something.txt')
        field = d._meta.get_field('myfile')
        field.save_form_data(d, None)
        self.assertEqual(d.myfile, 'something.txt')

    def test_changed(self):
        """
        FileField.save_form_data(), if passed a truthy value, updates its
        instance attribute.
        """
        d = Document(myfile='something.txt')
        self.assertEqual(d.myfile, 'something.txt')
        field = d._meta.get_field('myfile')
        field.save_form_data(d, 'else.txt')
        self.assertEqual(d.myfile, 'else.txt')

    def test_delete_when_file_unset(self):
        """
        Calling delete on an unset FileField should not call the file deletion
        process, but fail silently (#20660).
        """
        d = Document()
        d.myfile.delete()

    def test_refresh_from_db(self):
        d = Document.objects.create(myfile='something.txt')
        d.refresh_from_db()
        self.assertIs(d.myfile.instance, d)

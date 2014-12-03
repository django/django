from django.conf import settings
from django.test import SimpleTestCase

from .utils import render, setup


class ListIndexTests(SimpleTestCase):

    @setup({'list-index01': '{{ var.1 }}'})
    def test_list_index01(self):
        """
        List-index syntax allows a template to access a certain item of a
        subscriptable object.
        """
        output = render('list-index01', {'var': ['first item', 'second item']})
        self.assertEqual(output, 'second item')

    @setup({'list-index02': '{{ var.5 }}'})
    def test_list_index02(self):
        """
        Fail silently when the list index is out of range.
        """
        output = render('list-index02', {'var': ['first item', 'second item']})
        if settings.TEMPLATE_STRING_IF_INVALID:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')

    @setup({'list-index03': '{{ var.1 }}'})
    def test_list_index03(self):
        """
        Fail silently when the list index is out of range.
        """
        output = render('list-index03', {'var': None})
        if settings.TEMPLATE_STRING_IF_INVALID:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')

    @setup({'list-index04': '{{ var.1 }}'})
    def test_list_index04(self):
        """
        Fail silently when variable is a dict without the specified key.
        """
        output = render('list-index04', {'var': {}})
        if settings.TEMPLATE_STRING_IF_INVALID:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')

    @setup({'list-index05': '{{ var.1 }}'})
    def test_list_index05(self):
        """
        Dictionary lookup wins out when dict's key is a string.
        """
        output = render('list-index05', {'var': {'1': "hello"}})
        self.assertEqual(output, 'hello')

    @setup({'list-index06': '{{ var.1 }}'})
    def test_list_index06(self):
        """
        But list-index lookup wins out when dict's key is an int, which
        behind the scenes is really a dictionary lookup (for a dict)
        after converting the key to an int.
        """
        output = render('list-index06', {"var": {1: "hello"}})
        self.assertEqual(output, 'hello')

    @setup({'list-index07': '{{ var.1 }}'})
    def test_list_index07(self):
        """
        Dictionary lookup wins out when there is a string and int version
        of the key.
        """
        output = render('list-index07', {"var": {'1': "hello", 1: "world"}})
        self.assertEqual(output, 'hello')

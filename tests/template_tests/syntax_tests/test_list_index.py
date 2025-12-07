from django.test import SimpleTestCase

from ..utils import setup


class ListIndexTests(SimpleTestCase):
    @setup({"list-index01": "{{ var.1 }}"})
    def test_list_index01(self):
        """
        List-index syntax allows a template to access a certain item of a
        subscriptable object.
        """
        output = self.engine.render_to_string(
            "list-index01", {"var": ["first item", "second item"]}
        )
        self.assertEqual(output, "second item")

    @setup({"list-index02": "{{ var.5 }}"})
    def test_list_index02(self):
        """
        Fail silently when the list index is out of range.
        """
        output = self.engine.render_to_string(
            "list-index02", {"var": ["first item", "second item"]}
        )
        if self.engine.string_if_invalid:
            self.assertEqual(output, "INVALID")
        else:
            self.assertEqual(output, "")

    @setup({"list-index03": "{{ var.1 }}"})
    def test_list_index03(self):
        """
        Fail silently when the list index is out of range.
        """
        output = self.engine.render_to_string("list-index03", {"var": None})
        if self.engine.string_if_invalid:
            self.assertEqual(output, "INVALID")
        else:
            self.assertEqual(output, "")

    @setup({"list-index04": "{{ var.1 }}"})
    def test_list_index04(self):
        """
        Fail silently when variable is a dict without the specified key.
        """
        output = self.engine.render_to_string("list-index04", {"var": {}})
        if self.engine.string_if_invalid:
            self.assertEqual(output, "INVALID")
        else:
            self.assertEqual(output, "")

    @setup({"list-index05": "{{ var.1 }}"})
    def test_list_index05(self):
        """
        Dictionary lookup wins out when dict's key is a string.
        """
        output = self.engine.render_to_string("list-index05", {"var": {"1": "hello"}})
        self.assertEqual(output, "hello")

    @setup({"list-index06": "{{ var.1 }}"})
    def test_list_index06(self):
        """
        But list-index lookup wins out when dict's key is an int, which
        behind the scenes is really a dictionary lookup (for a dict)
        after converting the key to an int.
        """
        output = self.engine.render_to_string("list-index06", {"var": {1: "hello"}})
        self.assertEqual(output, "hello")

    @setup({"list-index07": "{{ var.1 }}"})
    def test_list_index07(self):
        """
        Dictionary lookup wins out when there is a string and int version
        of the key.
        """
        output = self.engine.render_to_string(
            "list-index07", {"var": {"1": "hello", 1: "world"}}
        )
        self.assertEqual(output, "hello")

from django.test import SimpleTestCase

from ..utils import setup


class SpaceIntTest(SimpleTestCase):
    @setup({"spaceint01": "{{ i|spaceint }}"})
    def test_spaceint_01(self):
        output = self.engine.render_to_string("spaceint01", {"i": 1234})
        self.assertEqual(output, "1 234")

    @setup({"spaceint02": "{{ i|spaceint:3 }}"})
    def test_spaceint_02(self):
        output = self.engine.render_to_string("spaceint02", {"i": 1234})
        self.assertEqual(output, "1 234")

    @setup({"spaceint03": "{{ i|spaceint:'3' }}"})
    def test_spaceint_03(self):
        output = self.engine.render_to_string("spaceint03", {"i": 1234})
        self.assertEqual(output, "1 234")

    @setup({"spaceint04": "{{ i|spaceint }}"})
    def test_spaceint_04(self):
        output = self.engine.render_to_string("spaceint04", {"i": -1234})
        self.assertEqual(output, "-1 234")

    @setup({"spaceint05": "{{ i|spaceint }}"})
    def test_spaceint_05(self):
        output = self.engine.render_to_string("spaceint05", {"i": "-1234"})
        self.assertEqual(output, "-1 234")

    @setup({"spaceint06": "{{ i|spaceint }}"})
    def test_spaceint_06(self):
        output = self.engine.render_to_string("spaceint06", {"i": "12 34"})
        self.assertEqual(output, "1 234")

    @setup({"spaceint07": "{{ i|spaceint }}"})
    def test_spaceint_07(self):
        output = self.engine.render_to_string("spaceint07", {"i": "1234"})
        self.assertEqual(output, "1 234")

    @setup({"spaceint08": "{{ i|spaceint:2 }}"})
    def test_spaceint_08(self):
        output = self.engine.render_to_string("spaceint08", {"i": 1234})
        self.assertEqual(output, "12 34")

    @setup({"spaceint09": "{{ i|spaceint:4 }}"})
    def test_spaceint_09(self):
        output = self.engine.render_to_string("spaceint09", {"i": 1234})
        self.assertEqual(output, "1234")

    @setup({"spaceint10": "{{ i|spaceint:4 }}"})
    def test_spaceint_10(self):
        output = self.engine.render_to_string("spaceint10", {"i": 12345678})
        self.assertEqual(output, "1234 5678")

    @setup({"spaceint11": "{{ i|spaceint:5 }}"})
    def test_spaceint_11(self):
        output = self.engine.render_to_string("spaceint11", {"i": 1234})
        self.assertEqual(output, "1234")

    @setup({"spaceint12": "{{ i|spaceint }}"})
    def test_spaceint_12(self):
        output = self.engine.render_to_string("spaceint12", {"i": -123})
        self.assertEqual(output, "-123")

    @setup({"spaceint13": "{{ i|spaceint }}"})
    def test_spaceint_13(self):
        output = self.engine.render_to_string("spaceint13", {"i": 12345})
        self.assertEqual(output, "12 345")

    @setup({"spaceint14": "{{ i|spaceint }}"})
    def test_spaceint_14(self):
        output = self.engine.render_to_string("spaceint14", {"i": 123456})
        self.assertEqual(output, "123 456")

    @setup({"spaceint15": "{{ i|spaceint }}"})
    def test_spaceint_15(self):
        output = self.engine.render_to_string("spaceint15", {"i": 1234567})
        self.assertEqual(output, "1 234 567")

    @setup({"spaceint16": "{{ i|spaceint }}"})
    def test_spaceint_16(self):
        output = self.engine.render_to_string("spaceint16", {
            "i": 123456789123456789123456789123456789123456789123456789
        })
        self.assertEqual(
            output,
            "123 456 789 123 456 789 123 456 789 123 456 789 123 456 789 123 456 789"
        )

    @setup({"spaceint17": "{{ i|spaceint }}"})
    def test_spaceint_17(self):
        output = self.engine.render_to_string("spaceint17", {"i": "string"})
        self.assertEqual(output, "")

    @setup({"spaceint18": "{{ i|spaceint:'string' }}"})
    def test_spaceint_18(self):
        output = self.engine.render_to_string("spaceint18", {"i": 1234})
        self.assertEqual(output, "")

    @setup({"spaceint19": "{{ i|spaceint }}"})
    def test_spaceint_19(self):
        output = self.engine.render_to_string("spaceint19", {"i": "-12-34"})
        self.assertEqual(output, "")

    @setup({"spaceint20": "{{ i|spaceint:-2 }}"})
    def test_spaceint_20(self):
        output = self.engine.render_to_string("spaceint20", {"i": 1234})
        self.assertEqual(output, "")

    @setup({"spaceint21": "{{ i|spaceint:0 }}"})
    def test_spaceint_21(self):
        output = self.engine.render_to_string("spaceint21", {"i": 1234})
        self.assertEqual(output, "")

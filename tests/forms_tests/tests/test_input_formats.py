from datetime import date, datetime, time

from django import forms
from django.test import SimpleTestCase, override_settings
from django.utils.translation import activate, deactivate


@override_settings(TIME_INPUT_FORMATS=["%I:%M:%S %p", "%I:%M %p"], USE_L10N=True)
class LocalizedTimeTests(SimpleTestCase):
    def setUp(self):
        # nl/formats.py has customized TIME_INPUT_FORMATS:
        # ['%H:%M:%S', '%H.%M:%S', '%H.%M', '%H:%M']
        activate('nl')

    def tearDown(self):
        deactivate()

    def test_timeField(self):
        "TimeFields can parse dates in the default format"
        f = forms.TimeField()
        # Parse a time in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('1:30:05 PM')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13:30:05')
        self.assertEqual(result, time(13, 30, 5))

        # Check that the parsed result does a round trip
        text = f.widget.format_value(result)
        self.assertEqual(text, '13:30:05')

        # Parse a time in a valid, but non-default format, get a parsed result
        result = f.clean('13:30')
        self.assertEqual(result, time(13, 30, 0))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "13:30:00")

        # ISO formats are accepted, even if not specified in formats.py
        result = f.clean('13:30:05.000155')
        self.assertEqual(result, time(13, 30, 5, 155))

    def test_localized_timeField(self):
        "Localized TimeFields act as unlocalized widgets"
        f = forms.TimeField(localize=True)
        # Parse a time in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('1:30:05 PM')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13:30:05')
        self.assertEqual(result, time(13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, '13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13:30')
        self.assertEqual(result, time(13, 30, 0))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "13:30:00")

    def test_timeField_with_inputformat(self):
        "TimeFields with manually specified input formats can accept those formats"
        f = forms.TimeField(input_formats=["%H.%M.%S", "%H.%M"])
        # Parse a time in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('1:30:05 PM')
        with self.assertRaises(forms.ValidationError):
            f.clean('13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30.05')
        self.assertEqual(result, time(13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "13:30:05")

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30')
        self.assertEqual(result, time(13, 30, 0))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "13:30:00")

    def test_localized_timeField_with_inputformat(self):
        "Localized TimeFields with manually specified input formats can accept those formats"
        f = forms.TimeField(input_formats=["%H.%M.%S", "%H.%M"], localize=True)
        # Parse a time in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('1:30:05 PM')
        with self.assertRaises(forms.ValidationError):
            f.clean('13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30.05')
        self.assertEqual(result, time(13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "13:30:05")

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30')
        self.assertEqual(result, time(13, 30, 0))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "13:30:00")


@override_settings(TIME_INPUT_FORMATS=["%I:%M:%S %p", "%I:%M %p"])
class CustomTimeInputFormatsTests(SimpleTestCase):
    def test_timeField(self):
        "TimeFields can parse dates in the default format"
        f = forms.TimeField()
        # Parse a time in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('1:30:05 PM')
        self.assertEqual(result, time(13, 30, 5))

        # Check that the parsed result does a round trip
        text = f.widget.format_value(result)
        self.assertEqual(text, '01:30:05 PM')

        # Parse a time in a valid, but non-default format, get a parsed result
        result = f.clean('1:30 PM')
        self.assertEqual(result, time(13, 30, 0))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "01:30:00 PM")

    def test_localized_timeField(self):
        "Localized TimeFields act as unlocalized widgets"
        f = forms.TimeField(localize=True)
        # Parse a time in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('1:30:05 PM')
        self.assertEqual(result, time(13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, '01:30:05 PM')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('01:30 PM')
        self.assertEqual(result, time(13, 30, 0))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "01:30:00 PM")

    def test_timeField_with_inputformat(self):
        "TimeFields with manually specified input formats can accept those formats"
        f = forms.TimeField(input_formats=["%H.%M.%S", "%H.%M"])
        # Parse a time in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('1:30:05 PM')
        with self.assertRaises(forms.ValidationError):
            f.clean('13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30.05')
        self.assertEqual(result, time(13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "01:30:05 PM")

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30')
        self.assertEqual(result, time(13, 30, 0))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "01:30:00 PM")

    def test_localized_timeField_with_inputformat(self):
        "Localized TimeFields with manually specified input formats can accept those formats"
        f = forms.TimeField(input_formats=["%H.%M.%S", "%H.%M"], localize=True)
        # Parse a time in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('1:30:05 PM')
        with self.assertRaises(forms.ValidationError):
            f.clean('13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30.05')
        self.assertEqual(result, time(13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "01:30:05 PM")

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30')
        self.assertEqual(result, time(13, 30, 0))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "01:30:00 PM")


class SimpleTimeFormatTests(SimpleTestCase):
    def test_timeField(self):
        "TimeFields can parse dates in the default format"
        f = forms.TimeField()
        # Parse a time in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('1:30:05 PM')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13:30:05')
        self.assertEqual(result, time(13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "13:30:05")

        # Parse a time in a valid, but non-default format, get a parsed result
        result = f.clean('13:30')
        self.assertEqual(result, time(13, 30, 0))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "13:30:00")

    def test_localized_timeField(self):
        "Localized TimeFields in a non-localized environment act as unlocalized widgets"
        f = forms.TimeField()
        # Parse a time in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('1:30:05 PM')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13:30:05')
        self.assertEqual(result, time(13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "13:30:05")

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13:30')
        self.assertEqual(result, time(13, 30, 0))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "13:30:00")

    def test_timeField_with_inputformat(self):
        "TimeFields with manually specified input formats can accept those formats"
        f = forms.TimeField(input_formats=["%I:%M:%S %p", "%I:%M %p"])
        # Parse a time in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('1:30:05 PM')
        self.assertEqual(result, time(13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "13:30:05")

        # Parse a time in a valid format, get a parsed result
        result = f.clean('1:30 PM')
        self.assertEqual(result, time(13, 30, 0))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "13:30:00")

    def test_localized_timeField_with_inputformat(self):
        "Localized TimeFields with manually specified input formats can accept those formats"
        f = forms.TimeField(input_formats=["%I:%M:%S %p", "%I:%M %p"], localize=True)
        # Parse a time in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('1:30:05 PM')
        self.assertEqual(result, time(13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "13:30:05")

        # Parse a time in a valid format, get a parsed result
        result = f.clean('1:30 PM')
        self.assertEqual(result, time(13, 30, 0))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "13:30:00")


@override_settings(DATE_INPUT_FORMATS=["%d/%m/%Y", "%d-%m-%Y"], USE_L10N=True)
class LocalizedDateTests(SimpleTestCase):
    def setUp(self):
        activate('de')

    def tearDown(self):
        deactivate()

    def test_dateField(self):
        "DateFields can parse dates in the default format"
        f = forms.DateField()
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('21/12/2010')

        # ISO formats are accepted, even if not specified in formats.py
        self.assertEqual(f.clean('2010-12-21'), date(2010, 12, 21))

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip
        text = f.widget.format_value(result)
        self.assertEqual(text, '21.12.2010')

        # Parse a date in a valid, but non-default format, get a parsed result
        result = f.clean('21.12.10')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010")

    def test_localized_dateField(self):
        "Localized DateFields act as unlocalized widgets"
        f = forms.DateField(localize=True)
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('21/12/2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, '21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.10')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010")

    def test_dateField_with_inputformat(self):
        "DateFields with manually specified input formats can accept those formats"
        f = forms.DateField(input_formats=["%m.%d.%Y", "%m-%d-%Y"])
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21')
        with self.assertRaises(forms.ValidationError):
            f.clean('21/12/2010')
        with self.assertRaises(forms.ValidationError):
            f.clean('21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12.21.2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12-21-2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010")

    def test_localized_dateField_with_inputformat(self):
        "Localized DateFields with manually specified input formats can accept those formats"
        f = forms.DateField(input_formats=["%m.%d.%Y", "%m-%d-%Y"], localize=True)
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21')
        with self.assertRaises(forms.ValidationError):
            f.clean('21/12/2010')
        with self.assertRaises(forms.ValidationError):
            f.clean('21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12.21.2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12-21-2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010")


@override_settings(DATE_INPUT_FORMATS=["%d.%m.%Y", "%d-%m-%Y"])
class CustomDateInputFormatsTests(SimpleTestCase):
    def test_dateField(self):
        "DateFields can parse dates in the default format"
        f = forms.DateField()
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip
        text = f.widget.format_value(result)
        self.assertEqual(text, '21.12.2010')

        # Parse a date in a valid, but non-default format, get a parsed result
        result = f.clean('21-12-2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010")

    def test_localized_dateField(self):
        "Localized DateFields act as unlocalized widgets"
        f = forms.DateField(localize=True)
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, '21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21-12-2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010")

    def test_dateField_with_inputformat(self):
        "DateFields with manually specified input formats can accept those formats"
        f = forms.DateField(input_formats=["%m.%d.%Y", "%m-%d-%Y"])
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('21.12.2010')
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12.21.2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12-21-2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010")

    def test_localized_dateField_with_inputformat(self):
        "Localized DateFields with manually specified input formats can accept those formats"
        f = forms.DateField(input_formats=["%m.%d.%Y", "%m-%d-%Y"], localize=True)
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('21.12.2010')
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12.21.2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12-21-2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010")


class SimpleDateFormatTests(SimpleTestCase):
    def test_dateField(self):
        "DateFields can parse dates in the default format"
        f = forms.DateField()
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('2010-12-21')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21")

        # Parse a date in a valid, but non-default format, get a parsed result
        result = f.clean('12/21/2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21")

    def test_localized_dateField(self):
        "Localized DateFields in a non-localized environment act as unlocalized widgets"
        f = forms.DateField()
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('2010-12-21')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12/21/2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21")

    def test_dateField_with_inputformat(self):
        "DateFields with manually specified input formats can accept those formats"
        f = forms.DateField(input_formats=["%d.%m.%Y", "%d-%m-%Y"])
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21-12-2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21")

    def test_localized_dateField_with_inputformat(self):
        "Localized DateFields with manually specified input formats can accept those formats"
        f = forms.DateField(input_formats=["%d.%m.%Y", "%d-%m-%Y"], localize=True)
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21-12-2010')
        self.assertEqual(result, date(2010, 12, 21))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21")


@override_settings(DATETIME_INPUT_FORMATS=["%I:%M:%S %p %d/%m/%Y", "%I:%M %p %d-%m-%Y"], USE_L10N=True)
class LocalizedDateTimeTests(SimpleTestCase):
    def setUp(self):
        activate('de')

    def tearDown(self):
        deactivate()

    def test_dateTimeField(self):
        "DateTimeFields can parse dates in the default format"
        f = forms.DateTimeField()
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('1:30:05 PM 21/12/2010')

        # ISO formats are accepted, even if not specified in formats.py
        self.assertEqual(f.clean('2010-12-21 13:30:05'), datetime(2010, 12, 21, 13, 30, 5))

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010 13:30:05')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30, 5))

        # Check that the parsed result does a round trip
        text = f.widget.format_value(result)
        self.assertEqual(text, '21.12.2010 13:30:05')

        # Parse a date in a valid, but non-default format, get a parsed result
        result = f.clean('21.12.2010 13:30')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010 13:30:00")

    def test_localized_dateTimeField(self):
        "Localized DateTimeFields act as unlocalized widgets"
        f = forms.DateTimeField(localize=True)
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('1:30:05 PM 21/12/2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010 13:30:05')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, '21.12.2010 13:30:05')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010 13:30')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010 13:30:00")

    def test_dateTimeField_with_inputformat(self):
        "DateTimeFields with manually specified input formats can accept those formats"
        f = forms.DateTimeField(input_formats=["%H.%M.%S %m.%d.%Y", "%H.%M %m-%d-%Y"])
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21 13:30:05 13:30:05')
        with self.assertRaises(forms.ValidationError):
            f.clean('1:30:05 PM 21/12/2010')
        with self.assertRaises(forms.ValidationError):
            f.clean('13:30:05 21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('13.30.05 12.21.2010')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010 13:30:05")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('13.30 12-21-2010')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010 13:30:00")

    def test_localized_dateTimeField_with_inputformat(self):
        "Localized DateTimeFields with manually specified input formats can accept those formats"
        f = forms.DateTimeField(input_formats=["%H.%M.%S %m.%d.%Y", "%H.%M %m-%d-%Y"], localize=True)
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21 13:30:05')
        with self.assertRaises(forms.ValidationError):
            f.clean('1:30:05 PM 21/12/2010')
        with self.assertRaises(forms.ValidationError):
            f.clean('13:30:05 21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('13.30.05 12.21.2010')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010 13:30:05")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('13.30 12-21-2010')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "21.12.2010 13:30:00")


@override_settings(DATETIME_INPUT_FORMATS=["%I:%M:%S %p %d/%m/%Y", "%I:%M %p %d-%m-%Y"])
class CustomDateTimeInputFormatsTests(SimpleTestCase):
    def test_dateTimeField(self):
        "DateTimeFields can parse dates in the default format"
        f = forms.DateTimeField()
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21 13:30:05')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('1:30:05 PM 21/12/2010')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30, 5))

        # Check that the parsed result does a round trip
        text = f.widget.format_value(result)
        self.assertEqual(text, '01:30:05 PM 21/12/2010')

        # Parse a date in a valid, but non-default format, get a parsed result
        result = f.clean('1:30 PM 21-12-2010')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "01:30:00 PM 21/12/2010")

    def test_localized_dateTimeField(self):
        "Localized DateTimeFields act as unlocalized widgets"
        f = forms.DateTimeField(localize=True)
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21 13:30:05')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('1:30:05 PM 21/12/2010')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, '01:30:05 PM 21/12/2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('1:30 PM 21-12-2010')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "01:30:00 PM 21/12/2010")

    def test_dateTimeField_with_inputformat(self):
        "DateTimeFields with manually specified input formats can accept those formats"
        f = forms.DateTimeField(input_formats=["%m.%d.%Y %H:%M:%S", "%m-%d-%Y %H:%M"])
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('13:30:05 21.12.2010')
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21 13:30:05')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12.21.2010 13:30:05')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "01:30:05 PM 21/12/2010")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12-21-2010 13:30')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "01:30:00 PM 21/12/2010")

    def test_localized_dateTimeField_with_inputformat(self):
        "Localized DateTimeFields with manually specified input formats can accept those formats"
        f = forms.DateTimeField(input_formats=["%m.%d.%Y %H:%M:%S", "%m-%d-%Y %H:%M"], localize=True)
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('13:30:05 21.12.2010')
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21 13:30:05')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12.21.2010 13:30:05')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "01:30:05 PM 21/12/2010")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12-21-2010 13:30')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "01:30:00 PM 21/12/2010")


class SimpleDateTimeFormatTests(SimpleTestCase):
    def test_dateTimeField(self):
        "DateTimeFields can parse dates in the default format"
        f = forms.DateTimeField()
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('13:30:05 21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('2010-12-21 13:30:05')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:05")

        # Parse a date in a valid, but non-default format, get a parsed result
        result = f.clean('12/21/2010 13:30:05')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30, 5))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:05")

    def test_localized_dateTimeField(self):
        "Localized DateTimeFields in a non-localized environment act as unlocalized widgets"
        f = forms.DateTimeField()
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('13:30:05 21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('2010-12-21 13:30:05')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:05")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12/21/2010 13:30:05')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30, 5))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:05")

    def test_dateTimeField_with_inputformat(self):
        "DateTimeFields with manually specified input formats can accept those formats"
        f = forms.DateTimeField(input_formats=["%I:%M:%S %p %d.%m.%Y", "%I:%M %p %d-%m-%Y"])
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21 13:30:05')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('1:30:05 PM 21.12.2010')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:05")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('1:30 PM 21-12-2010')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:00")

    def test_localized_dateTimeField_with_inputformat(self):
        "Localized DateTimeFields with manually specified input formats can accept those formats"
        f = forms.DateTimeField(input_formats=["%I:%M:%S %p %d.%m.%Y", "%I:%M %p %d-%m-%Y"], localize=True)
        # Parse a date in an unaccepted format; get an error
        with self.assertRaises(forms.ValidationError):
            f.clean('2010-12-21 13:30:05')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('1:30:05 PM 21.12.2010')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30, 5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:05")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('1:30 PM 21-12-2010')
        self.assertEqual(result, datetime(2010, 12, 21, 13, 30))

        # Check that the parsed result does a round trip to default format
        text = f.widget.format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:00")

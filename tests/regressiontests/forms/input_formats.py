from datetime import time, date, datetime

from django import forms
from django.conf import settings
from django.utils.translation import activate, deactivate
from django.utils.unittest import TestCase


class LocalizedTimeTests(TestCase):
    def setUp(self):
        self.old_TIME_INPUT_FORMATS = settings.TIME_INPUT_FORMATS
        self.old_USE_L10N = settings.USE_L10N

        settings.TIME_INPUT_FORMATS = ["%I:%M:%S %p", "%I:%M %p"]
        settings.USE_L10N = True

        activate('de')

    def tearDown(self):
        settings.TIME_INPUT_FORMATS = self.old_TIME_INPUT_FORMATS
        settings.USE_L10N = self.old_USE_L10N

        deactivate()

    def test_timeField(self):
        "TimeFields can parse dates in the default format"
        f = forms.TimeField()
        # Parse a time in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '1:30:05 PM')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13:30:05')
        self.assertEqual(result, time(13,30,5))

        # Check that the parsed result does a round trip
        text = f.widget._format_value(result)
        self.assertEqual(text, '13:30:05')

        # Parse a time in a valid, but non-default format, get a parsed result
        result = f.clean('13:30')
        self.assertEqual(result, time(13,30,0))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "13:30:00")

    def test_localized_timeField(self):
        "Localized TimeFields act as unlocalized widgets"
        f = forms.TimeField(localize=True)
        # Parse a time in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '1:30:05 PM')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13:30:05')
        self.assertEqual(result, time(13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, '13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13:30')
        self.assertEqual(result, time(13,30,0))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "13:30:00")

    def test_timeField_with_inputformat(self):
        "TimeFields with manually specified input formats can accept those formats"
        f = forms.TimeField(input_formats=["%H.%M.%S", "%H.%M"])
        # Parse a time in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '1:30:05 PM')
        self.assertRaises(forms.ValidationError, f.clean, '13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30.05')
        self.assertEqual(result, time(13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "13:30:05")

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30')
        self.assertEqual(result, time(13,30,0))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "13:30:00")

    def test_localized_timeField_with_inputformat(self):
        "Localized TimeFields with manually specified input formats can accept those formats"
        f = forms.TimeField(input_formats=["%H.%M.%S", "%H.%M"], localize=True)
        # Parse a time in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '1:30:05 PM')
        self.assertRaises(forms.ValidationError, f.clean, '13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30.05')
        self.assertEqual(result, time(13,30,5))

        # # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "13:30:05")

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30')
        self.assertEqual(result, time(13,30,0))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "13:30:00")


class CustomTimeInputFormatsTests(TestCase):
    def setUp(self):
        self.old_TIME_INPUT_FORMATS = settings.TIME_INPUT_FORMATS
        settings.TIME_INPUT_FORMATS = ["%I:%M:%S %p", "%I:%M %p"]

    def tearDown(self):
        settings.TIME_INPUT_FORMATS = self.old_TIME_INPUT_FORMATS

    def test_timeField(self):
        "TimeFields can parse dates in the default format"
        f = forms.TimeField()
        # Parse a time in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('1:30:05 PM')
        self.assertEqual(result, time(13,30,5))

        # Check that the parsed result does a round trip
        text = f.widget._format_value(result)
        self.assertEqual(text, '01:30:05 PM')

        # Parse a time in a valid, but non-default format, get a parsed result
        result = f.clean('1:30 PM')
        self.assertEqual(result, time(13,30,0))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "01:30:00 PM")

    def test_localized_timeField(self):
        "Localized TimeFields act as unlocalized widgets"
        f = forms.TimeField(localize=True)
        # Parse a time in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('1:30:05 PM')
        self.assertEqual(result, time(13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, '01:30:05 PM')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('01:30 PM')
        self.assertEqual(result, time(13,30,0))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "01:30:00 PM")

    def test_timeField_with_inputformat(self):
        "TimeFields with manually specified input formats can accept those formats"
        f = forms.TimeField(input_formats=["%H.%M.%S", "%H.%M"])
        # Parse a time in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '1:30:05 PM')
        self.assertRaises(forms.ValidationError, f.clean, '13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30.05')
        self.assertEqual(result, time(13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "01:30:05 PM")

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30')
        self.assertEqual(result, time(13,30,0))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "01:30:00 PM")

    def test_localized_timeField_with_inputformat(self):
        "Localized TimeFields with manually specified input formats can accept those formats"
        f = forms.TimeField(input_formats=["%H.%M.%S", "%H.%M"], localize=True)
        # Parse a time in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '1:30:05 PM')
        self.assertRaises(forms.ValidationError, f.clean, '13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30.05')
        self.assertEqual(result, time(13,30,5))

        # # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "01:30:05 PM")

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13.30')
        self.assertEqual(result, time(13,30,0))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "01:30:00 PM")


class SimpleTimeFormatTests(TestCase):
    def test_timeField(self):
        "TimeFields can parse dates in the default format"
        f = forms.TimeField()
        # Parse a time in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '1:30:05 PM')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13:30:05')
        self.assertEqual(result, time(13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "13:30:05")

        # Parse a time in a valid, but non-default format, get a parsed result
        result = f.clean('13:30')
        self.assertEqual(result, time(13,30,0))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "13:30:00")

    def test_localized_timeField(self):
        "Localized TimeFields in a non-localized environment act as unlocalized widgets"
        f = forms.TimeField()
        # Parse a time in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '1:30:05 PM')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13:30:05')
        self.assertEqual(result, time(13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "13:30:05")

        # Parse a time in a valid format, get a parsed result
        result = f.clean('13:30')
        self.assertEqual(result, time(13,30,0))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "13:30:00")

    def test_timeField_with_inputformat(self):
        "TimeFields with manually specified input formats can accept those formats"
        f = forms.TimeField(input_formats=["%I:%M:%S %p", "%I:%M %p"])
        # Parse a time in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('1:30:05 PM')
        self.assertEqual(result, time(13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "13:30:05")

        # Parse a time in a valid format, get a parsed result
        result = f.clean('1:30 PM')
        self.assertEqual(result, time(13,30,0))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "13:30:00")

    def test_localized_timeField_with_inputformat(self):
        "Localized TimeFields with manually specified input formats can accept those formats"
        f = forms.TimeField(input_formats=["%I:%M:%S %p", "%I:%M %p"], localize=True)
        # Parse a time in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '13:30:05')

        # Parse a time in a valid format, get a parsed result
        result = f.clean('1:30:05 PM')
        self.assertEqual(result, time(13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "13:30:05")

        # Parse a time in a valid format, get a parsed result
        result = f.clean('1:30 PM')
        self.assertEqual(result, time(13,30,0))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "13:30:00")


class LocalizedDateTests(TestCase):
    def setUp(self):
        self.old_DATE_INPUT_FORMATS = settings.DATE_INPUT_FORMATS
        self.old_USE_L10N = settings.USE_L10N

        settings.DATE_INPUT_FORMATS = ["%d/%m/%Y", "%d-%m-%Y"]
        settings.USE_L10N = True

        activate('de')

    def tearDown(self):
        settings.DATE_INPUT_FORMATS = self.old_DATE_INPUT_FORMATS
        settings.USE_L10N = self.old_USE_L10N

        deactivate()

    def test_dateField(self):
        "DateFields can parse dates in the default format"
        f = forms.DateField()
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '21/12/2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip
        text = f.widget._format_value(result)
        self.assertEqual(text, '21.12.2010')

        # Parse a date in a valid, but non-default format, get a parsed result
        result = f.clean('21.12.10')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010")

    def test_localized_dateField(self):
        "Localized DateFields act as unlocalized widgets"
        f = forms.DateField(localize=True)
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '21/12/2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, '21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.10')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010")

    def test_dateField_with_inputformat(self):
        "DateFields with manually specified input formats can accept those formats"
        f = forms.DateField(input_formats=["%m.%d.%Y", "%m-%d-%Y"])
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21')
        self.assertRaises(forms.ValidationError, f.clean, '21/12/2010')
        self.assertRaises(forms.ValidationError, f.clean, '21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12.21.2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12-21-2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010")

    def test_localized_dateField_with_inputformat(self):
        "Localized DateFields with manually specified input formats can accept those formats"
        f = forms.DateField(input_formats=["%m.%d.%Y", "%m-%d-%Y"], localize=True)
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21')
        self.assertRaises(forms.ValidationError, f.clean, '21/12/2010')
        self.assertRaises(forms.ValidationError, f.clean, '21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12.21.2010')
        self.assertEqual(result, date(2010,12,21))

        # # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12-21-2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010")

class CustomDateInputFormatsTests(TestCase):
    def setUp(self):
        self.old_DATE_INPUT_FORMATS = settings.DATE_INPUT_FORMATS
        settings.DATE_INPUT_FORMATS = ["%d.%m.%Y", "%d-%m-%Y"]

    def tearDown(self):
        settings.DATE_INPUT_FORMATS = self.old_DATE_INPUT_FORMATS

    def test_dateField(self):
        "DateFields can parse dates in the default format"
        f = forms.DateField()
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip
        text = f.widget._format_value(result)
        self.assertEqual(text, '21.12.2010')

        # Parse a date in a valid, but non-default format, get a parsed result
        result = f.clean('21-12-2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010")

    def test_localized_dateField(self):
        "Localized DateFields act as unlocalized widgets"
        f = forms.DateField(localize=True)
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, '21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21-12-2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010")

    def test_dateField_with_inputformat(self):
        "DateFields with manually specified input formats can accept those formats"
        f = forms.DateField(input_formats=["%m.%d.%Y", "%m-%d-%Y"])
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '21.12.2010')
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12.21.2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12-21-2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010")

    def test_localized_dateField_with_inputformat(self):
        "Localized DateFields with manually specified input formats can accept those formats"
        f = forms.DateField(input_formats=["%m.%d.%Y", "%m-%d-%Y"], localize=True)
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '21.12.2010')
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12.21.2010')
        self.assertEqual(result, date(2010,12,21))

        # # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12-21-2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010")

class SimpleDateFormatTests(TestCase):
    def test_dateField(self):
        "DateFields can parse dates in the default format"
        f = forms.DateField()
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('2010-12-21')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21")

        # Parse a date in a valid, but non-default format, get a parsed result
        result = f.clean('12/21/2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21")

    def test_localized_dateField(self):
        "Localized DateFields in a non-localized environment act as unlocalized widgets"
        f = forms.DateField()
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('2010-12-21')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12/21/2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21")

    def test_dateField_with_inputformat(self):
        "DateFields with manually specified input formats can accept those formats"
        f = forms.DateField(input_formats=["%d.%m.%Y", "%d-%m-%Y"])
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21-12-2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21")

    def test_localized_dateField_with_inputformat(self):
        "Localized DateFields with manually specified input formats can accept those formats"
        f = forms.DateField(input_formats=["%d.%m.%Y", "%d-%m-%Y"], localize=True)
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21-12-2010')
        self.assertEqual(result, date(2010,12,21))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21")

class LocalizedDateTimeTests(TestCase):
    def setUp(self):
        self.old_DATETIME_INPUT_FORMATS = settings.DATETIME_INPUT_FORMATS
        self.old_USE_L10N = settings.USE_L10N

        settings.DATETIME_INPUT_FORMATS = ["%I:%M:%S %p %d/%m/%Y", "%I:%M %p %d-%m-%Y"]
        settings.USE_L10N = True

        activate('de')

    def tearDown(self):
        settings.DATETIME_INPUT_FORMATS = self.old_DATETIME_INPUT_FORMATS
        settings.USE_L10N = self.old_USE_L10N

        deactivate()

    def test_dateTimeField(self):
        "DateTimeFields can parse dates in the default format"
        f = forms.DateTimeField()
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '1:30:05 PM 21/12/2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010 13:30:05')
        self.assertEqual(result, datetime(2010,12,21,13,30,5))

        # Check that the parsed result does a round trip
        text = f.widget._format_value(result)
        self.assertEqual(text, '21.12.2010 13:30:05')

        # Parse a date in a valid, but non-default format, get a parsed result
        result = f.clean('21.12.2010 13:30')
        self.assertEqual(result, datetime(2010,12,21,13,30))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010 13:30:00")

    def test_localized_dateTimeField(self):
        "Localized DateTimeFields act as unlocalized widgets"
        f = forms.DateTimeField(localize=True)
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '1:30:05 PM 21/12/2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010 13:30:05')
        self.assertEqual(result, datetime(2010,12,21,13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, '21.12.2010 13:30:05')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('21.12.2010 13:30')
        self.assertEqual(result, datetime(2010,12,21,13,30))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010 13:30:00")

    def test_dateTimeField_with_inputformat(self):
        "DateTimeFields with manually specified input formats can accept those formats"
        f = forms.DateTimeField(input_formats=["%H.%M.%S %m.%d.%Y", "%H.%M %m-%d-%Y"])
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21 13:30:05 13:30:05')
        self.assertRaises(forms.ValidationError, f.clean, '1:30:05 PM 21/12/2010')
        self.assertRaises(forms.ValidationError, f.clean, '13:30:05 21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('13.30.05 12.21.2010')
        self.assertEqual(result, datetime(2010,12,21,13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010 13:30:05")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('13.30 12-21-2010')
        self.assertEqual(result, datetime(2010,12,21,13,30))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010 13:30:00")

    def test_localized_dateTimeField_with_inputformat(self):
        "Localized DateTimeFields with manually specified input formats can accept those formats"
        f = forms.DateTimeField(input_formats=["%H.%M.%S %m.%d.%Y", "%H.%M %m-%d-%Y"], localize=True)
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21 13:30:05')
        self.assertRaises(forms.ValidationError, f.clean, '1:30:05 PM 21/12/2010')
        self.assertRaises(forms.ValidationError, f.clean, '13:30:05 21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('13.30.05 12.21.2010')
        self.assertEqual(result, datetime(2010,12,21,13,30,5))

        # # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010 13:30:05")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('13.30 12-21-2010')
        self.assertEqual(result, datetime(2010,12,21,13,30))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "21.12.2010 13:30:00")


class CustomDateTimeInputFormatsTests(TestCase):
    def setUp(self):
        self.old_DATETIME_INPUT_FORMATS = settings.DATETIME_INPUT_FORMATS
        settings.DATETIME_INPUT_FORMATS = ["%I:%M:%S %p %d/%m/%Y", "%I:%M %p %d-%m-%Y"]

    def tearDown(self):
        settings.DATETIME_INPUT_FORMATS = self.old_DATETIME_INPUT_FORMATS

    def test_dateTimeField(self):
        "DateTimeFields can parse dates in the default format"
        f = forms.DateTimeField()
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21 13:30:05')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('1:30:05 PM 21/12/2010')
        self.assertEqual(result, datetime(2010,12,21,13,30,5))

        # Check that the parsed result does a round trip
        text = f.widget._format_value(result)
        self.assertEqual(text, '01:30:05 PM 21/12/2010')

        # Parse a date in a valid, but non-default format, get a parsed result
        result = f.clean('1:30 PM 21-12-2010')
        self.assertEqual(result, datetime(2010,12,21,13,30))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "01:30:00 PM 21/12/2010")

    def test_localized_dateTimeField(self):
        "Localized DateTimeFields act as unlocalized widgets"
        f = forms.DateTimeField(localize=True)
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21 13:30:05')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('1:30:05 PM 21/12/2010')
        self.assertEqual(result, datetime(2010,12,21,13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, '01:30:05 PM 21/12/2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('1:30 PM 21-12-2010')
        self.assertEqual(result, datetime(2010,12,21,13,30))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "01:30:00 PM 21/12/2010")

    def test_dateTimeField_with_inputformat(self):
        "DateTimeFields with manually specified input formats can accept those formats"
        f = forms.DateTimeField(input_formats=["%m.%d.%Y %H:%M:%S", "%m-%d-%Y %H:%M"])
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '13:30:05 21.12.2010')
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21 13:30:05')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12.21.2010 13:30:05')
        self.assertEqual(result, datetime(2010,12,21,13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "01:30:05 PM 21/12/2010")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12-21-2010 13:30')
        self.assertEqual(result, datetime(2010,12,21,13,30))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "01:30:00 PM 21/12/2010")

    def test_localized_dateTimeField_with_inputformat(self):
        "Localized DateTimeFields with manually specified input formats can accept those formats"
        f = forms.DateTimeField(input_formats=["%m.%d.%Y %H:%M:%S", "%m-%d-%Y %H:%M"], localize=True)
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '13:30:05 21.12.2010')
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21 13:30:05')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12.21.2010 13:30:05')
        self.assertEqual(result, datetime(2010,12,21,13,30,5))

        # # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "01:30:05 PM 21/12/2010")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12-21-2010 13:30')
        self.assertEqual(result, datetime(2010,12,21,13,30))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "01:30:00 PM 21/12/2010")

class SimpleDateTimeFormatTests(TestCase):
    def test_dateTimeField(self):
        "DateTimeFields can parse dates in the default format"
        f = forms.DateTimeField()
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '13:30:05 21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('2010-12-21 13:30:05')
        self.assertEqual(result, datetime(2010,12,21,13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:05")

        # Parse a date in a valid, but non-default format, get a parsed result
        result = f.clean('12/21/2010 13:30:05')
        self.assertEqual(result, datetime(2010,12,21,13,30,5))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:05")

    def test_localized_dateTimeField(self):
        "Localized DateTimeFields in a non-localized environment act as unlocalized widgets"
        f = forms.DateTimeField()
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '13:30:05 21.12.2010')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('2010-12-21 13:30:05')
        self.assertEqual(result, datetime(2010,12,21,13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:05")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('12/21/2010 13:30:05')
        self.assertEqual(result, datetime(2010,12,21,13,30,5))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:05")

    def test_dateTimeField_with_inputformat(self):
        "DateTimeFields with manually specified input formats can accept those formats"
        f = forms.DateTimeField(input_formats=["%I:%M:%S %p %d.%m.%Y", "%I:%M %p %d-%m-%Y"])
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21 13:30:05')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('1:30:05 PM 21.12.2010')
        self.assertEqual(result, datetime(2010,12,21,13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:05")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('1:30 PM 21-12-2010')
        self.assertEqual(result, datetime(2010,12,21,13,30))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:00")

    def test_localized_dateTimeField_with_inputformat(self):
        "Localized DateTimeFields with manually specified input formats can accept those formats"
        f = forms.DateTimeField(input_formats=["%I:%M:%S %p %d.%m.%Y", "%I:%M %p %d-%m-%Y"], localize=True)
        # Parse a date in an unaccepted format; get an error
        self.assertRaises(forms.ValidationError, f.clean, '2010-12-21 13:30:05')

        # Parse a date in a valid format, get a parsed result
        result = f.clean('1:30:05 PM 21.12.2010')
        self.assertEqual(result, datetime(2010,12,21,13,30,5))

        # Check that the parsed result does a round trip to the same format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:05")

        # Parse a date in a valid format, get a parsed result
        result = f.clean('1:30 PM 21-12-2010')
        self.assertEqual(result, datetime(2010,12,21,13,30))

        # Check that the parsed result does a round trip to default format
        text = f.widget._format_value(result)
        self.assertEqual(text, "2010-12-21 13:30:00")

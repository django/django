from datetime import date

from django.forms import DateField, Form, SelectDateWidget
from django.test import override_settings
from django.utils import translation
from django.utils.dates import MONTHS_AP

from .base import WidgetTest


class SelectDateWidgetTest(WidgetTest):
    maxDiff = None
    widget = SelectDateWidget(
        years=('2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016'),
    )

    def test_render_empty(self):
        self.check_html(self.widget, 'mydate', '', html=(
            """
            <select name="mydate_month" id="id_mydate_month">
                <option selected value="">---</option>
                <option value="1">January</option>
                <option value="2">February</option>
                <option value="3">March</option>
                <option value="4">April</option>
                <option value="5">May</option>
                <option value="6">June</option>
                <option value="7">July</option>
                <option value="8">August</option>
                <option value="9">September</option>
                <option value="10">October</option>
                <option value="11">November</option>
                <option value="12">December</option>
            </select>

            <select name="mydate_day" id="id_mydate_day">
                <option selected value="">---</option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4">4</option>
                <option value="5">5</option>
                <option value="6">6</option>
                <option value="7">7</option>
                <option value="8">8</option>
                <option value="9">9</option>
                <option value="10">10</option>
                <option value="11">11</option>
                <option value="12">12</option>
                <option value="13">13</option>
                <option value="14">14</option>
                <option value="15">15</option>
                <option value="16">16</option>
                <option value="17">17</option>
                <option value="18">18</option>
                <option value="19">19</option>
                <option value="20">20</option>
                <option value="21">21</option>
                <option value="22">22</option>
                <option value="23">23</option>
                <option value="24">24</option>
                <option value="25">25</option>
                <option value="26">26</option>
                <option value="27">27</option>
                <option value="28">28</option>
                <option value="29">29</option>
                <option value="30">30</option>
                <option value="31">31</option>
            </select>

            <select name="mydate_year" id="id_mydate_year">
                <option selected value="">---</option>
                <option value="2007">2007</option>
                <option value="2008">2008</option>
                <option value="2009">2009</option>
                <option value="2010">2010</option>
                <option value="2011">2011</option>
                <option value="2012">2012</option>
                <option value="2013">2013</option>
                <option value="2014">2014</option>
                <option value="2015">2015</option>
                <option value="2016">2016</option>
            </select>
            """
        ))

    def test_render_none(self):
        """
        Rendering the None or '' values should yield the same output.
        """
        self.assertHTMLEqual(
            self.widget.render('mydate', None),
            self.widget.render('mydate', ''),
        )

    def test_render_string(self):
        self.check_html(self.widget, 'mydate', '2010-04-15', html=(
            """
            <select name="mydate_month" id="id_mydate_month">
                <option value="">---</option>
                <option value="1">January</option>
                <option value="2">February</option>
                <option value="3">March</option>
                <option value="4" selected>April</option>
                <option value="5">May</option>
                <option value="6">June</option>
                <option value="7">July</option>
                <option value="8">August</option>
                <option value="9">September</option>
                <option value="10">October</option>
                <option value="11">November</option>
                <option value="12">December</option>
            </select>

            <select name="mydate_day" id="id_mydate_day">
                <option value="">---</option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4">4</option>
                <option value="5">5</option>
                <option value="6">6</option>
                <option value="7">7</option>
                <option value="8">8</option>
                <option value="9">9</option>
                <option value="10">10</option>
                <option value="11">11</option>
                <option value="12">12</option>
                <option value="13">13</option>
                <option value="14">14</option>
                <option value="15" selected>15</option>
                <option value="16">16</option>
                <option value="17">17</option>
                <option value="18">18</option>
                <option value="19">19</option>
                <option value="20">20</option>
                <option value="21">21</option>
                <option value="22">22</option>
                <option value="23">23</option>
                <option value="24">24</option>
                <option value="25">25</option>
                <option value="26">26</option>
                <option value="27">27</option>
                <option value="28">28</option>
                <option value="29">29</option>
                <option value="30">30</option>
                <option value="31">31</option>
            </select>

            <select name="mydate_year" id="id_mydate_year">
                <option value="">---</option>
                <option value="2007">2007</option>
                <option value="2008">2008</option>
                <option value="2009">2009</option>
                <option value="2010" selected>2010</option>
                <option value="2011">2011</option>
                <option value="2012">2012</option>
                <option value="2013">2013</option>
                <option value="2014">2014</option>
                <option value="2015">2015</option>
                <option value="2016">2016</option>
            </select>
            """
        ))

    def test_render_datetime(self):
        self.assertHTMLEqual(
            self.widget.render('mydate', date(2010, 4, 15)),
            self.widget.render('mydate', '2010-04-15'),
        )

    def test_render_invalid_date(self):
        """
        Invalid dates should still render the failed date.
        """
        self.check_html(self.widget, 'mydate', '2010-02-31', html=(
            """
            <select name="mydate_month" id="id_mydate_month">
                <option value="">---</option>
                <option value="1">January</option>
                <option value="2" selected>February</option>
                <option value="3">March</option>
                <option value="4">April</option>
                <option value="5">May</option>
                <option value="6">June</option>
                <option value="7">July</option>
                <option value="8">August</option>
                <option value="9">September</option>
                <option value="10">October</option>
                <option value="11">November</option>
                <option value="12">December</option>
            </select>

            <select name="mydate_day" id="id_mydate_day">
                <option value="">---</option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4">4</option>
                <option value="5">5</option>
                <option value="6">6</option>
                <option value="7">7</option>
                <option value="8">8</option>
                <option value="9">9</option>
                <option value="10">10</option>
                <option value="11">11</option>
                <option value="12">12</option>
                <option value="13">13</option>
                <option value="14">14</option>
                <option value="15">15</option>
                <option value="16">16</option>
                <option value="17">17</option>
                <option value="18">18</option>
                <option value="19">19</option>
                <option value="20">20</option>
                <option value="21">21</option>
                <option value="22">22</option>
                <option value="23">23</option>
                <option value="24">24</option>
                <option value="25">25</option>
                <option value="26">26</option>
                <option value="27">27</option>
                <option value="28">28</option>
                <option value="29">29</option>
                <option value="30">30</option>
                <option value="31" selected>31</option>
            </select>

            <select name="mydate_year" id="id_mydate_year">
                <option value="">---</option>
                <option value="2007">2007</option>
                <option value="2008">2008</option>
                <option value="2009">2009</option>
                <option value="2010" selected>2010</option>
                <option value="2011">2011</option>
                <option value="2012">2012</option>
                <option value="2013">2013</option>
                <option value="2014">2014</option>
                <option value="2015">2015</option>
                <option value="2016">2016</option>
            </select>
            """
        ))

    def test_custom_months(self):
        widget = SelectDateWidget(months=MONTHS_AP, years=('2013',))
        self.check_html(widget, 'mydate', '', html=(
            """
            <select name="mydate_month" id="id_mydate_month">
                <option selected value="">---</option>
                <option value="1">Jan.</option>
                <option value="2">Feb.</option>
                <option value="3">March</option>
                <option value="4">April</option>
                <option value="5">May</option>
                <option value="6">June</option>
                <option value="7">July</option>
                <option value="8">Aug.</option>
                <option value="9">Sept.</option>
                <option value="10">Oct.</option>
                <option value="11">Nov.</option>
                <option value="12">Dec.</option>
            </select>

            <select name="mydate_day" id="id_mydate_day">
                <option selected value="">---</option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4">4</option>
                <option value="5">5</option>
                <option value="6">6</option>
                <option value="7">7</option>
                <option value="8">8</option>
                <option value="9">9</option>
                <option value="10">10</option>
                <option value="11">11</option>
                <option value="12">12</option>
                <option value="13">13</option>
                <option value="14">14</option>
                <option value="15">15</option>
                <option value="16">16</option>
                <option value="17">17</option>
                <option value="18">18</option>
                <option value="19">19</option>
                <option value="20">20</option>
                <option value="21">21</option>
                <option value="22">22</option>
                <option value="23">23</option>
                <option value="24">24</option>
                <option value="25">25</option>
                <option value="26">26</option>
                <option value="27">27</option>
                <option value="28">28</option>
                <option value="29">29</option>
                <option value="30">30</option>
                <option value="31">31</option>
            </select>

            <select name="mydate_year" id="id_mydate_year">
                <option selected value="">---</option>
                <option value="2013">2013</option>
            </select>
            """
        ))

    def test_selectdate_required(self):
        class GetNotRequiredDate(Form):
            mydate = DateField(widget=SelectDateWidget, required=False)

        class GetRequiredDate(Form):
            mydate = DateField(widget=SelectDateWidget, required=True)

        self.assertFalse(GetNotRequiredDate().fields['mydate'].widget.is_required)
        self.assertTrue(GetRequiredDate().fields['mydate'].widget.is_required)

    def test_selectdate_required_placeholder(self):
        for required in (True, False):
            field = DateField(widget=SelectDateWidget(years=('2018', '2019')), required=required)
            self.check_html(field.widget, 'my_date', '', html=(
                """
                <select name="my_date_month" id="id_my_date_month" %(m_placeholder)s>
                    %(empty)s
                    <option value="1">January</option>
                    <option value="2">February</option>
                    <option value="3">March</option>
                    <option value="4">April</option>
                    <option value="5">May</option>
                    <option value="6">June</option>
                    <option value="7">July</option>
                    <option value="8">August</option>
                    <option value="9">September</option>
                    <option value="10">October</option>
                    <option value="11">November</option>
                    <option value="12">December</option>
                </select>
                <select name="my_date_day" id="id_my_date_day" %(d_placeholder)s>
                    %(empty)s
                    %(days_options)s
                </select>
                <select name="my_date_year" id="id_my_date_year" %(y_placeholder)s>
                    %(empty)s
                    <option value="2018">2018</option>
                    <option value="2019">2019</option>
                </select>
                """ % {
                    'days_options': '\n'.join(
                        '<option value="%s">%s</option>' % (i, i) for i in range(1, 32)
                    ),
                    'm_placeholder': 'placeholder="Month"' if required else '',
                    'd_placeholder': 'placeholder="Day"' if required else '',
                    'y_placeholder': 'placeholder="Year"' if required else '',
                    'empty': '' if required else '<option selected value="">---</option>',
                }
            ))

    def test_selectdate_empty_label(self):
        w = SelectDateWidget(years=('2014',), empty_label='empty_label')

        # Rendering the default state with empty_label set as string.
        self.assertInHTML('<option selected value="">empty_label</option>', w.render('mydate', ''), count=3)

        w = SelectDateWidget(years=('2014',), empty_label=('empty_year', 'empty_month', 'empty_day'))

        # Rendering the default state with empty_label tuple.
        self.assertHTMLEqual(
            w.render('mydate', ''),
            """
            <select name="mydate_month" id="id_mydate_month">
                <option selected value="">empty_month</option>
                <option value="1">January</option>
                <option value="2">February</option>
                <option value="3">March</option>
                <option value="4">April</option>
                <option value="5">May</option>
                <option value="6">June</option>
                <option value="7">July</option>
                <option value="8">August</option>
                <option value="9">September</option>
                <option value="10">October</option>
                <option value="11">November</option>
                <option value="12">December</option>
            </select>

            <select name="mydate_day" id="id_mydate_day">
                <option selected value="">empty_day</option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4">4</option>
                <option value="5">5</option>
                <option value="6">6</option>
                <option value="7">7</option>
                <option value="8">8</option>
                <option value="9">9</option>
                <option value="10">10</option>
                <option value="11">11</option>
                <option value="12">12</option>
                <option value="13">13</option>
                <option value="14">14</option>
                <option value="15">15</option>
                <option value="16">16</option>
                <option value="17">17</option>
                <option value="18">18</option>
                <option value="19">19</option>
                <option value="20">20</option>
                <option value="21">21</option>
                <option value="22">22</option>
                <option value="23">23</option>
                <option value="24">24</option>
                <option value="25">25</option>
                <option value="26">26</option>
                <option value="27">27</option>
                <option value="28">28</option>
                <option value="29">29</option>
                <option value="30">30</option>
                <option value="31">31</option>
            </select>

            <select name="mydate_year" id="id_mydate_year">
                <option selected value="">empty_year</option>
                <option value="2014">2014</option>
            </select>
            """,
        )

        with self.assertRaisesMessage(ValueError, 'empty_label list/tuple must have 3 elements.'):
            SelectDateWidget(years=('2014',), empty_label=('not enough', 'values'))

    @override_settings(USE_L10N=True)
    @translation.override('nl')
    def test_l10n(self):
        w = SelectDateWidget(
            years=('2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016')
        )
        self.assertEqual(
            w.value_from_datadict({'date_year': '2010', 'date_month': '8', 'date_day': '13'}, {}, 'date'),
            '13-08-2010',
        )

        self.assertHTMLEqual(
            w.render('date', '13-08-2010'),
            """
            <select name="date_day" id="id_date_day">
                <option value="">---</option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4">4</option>
                <option value="5">5</option>
                <option value="6">6</option>
                <option value="7">7</option>
                <option value="8">8</option>
                <option value="9">9</option>
                <option value="10">10</option>
                <option value="11">11</option>
                <option value="12">12</option>
                <option value="13" selected>13</option>
                <option value="14">14</option>
                <option value="15">15</option>
                <option value="16">16</option>
                <option value="17">17</option>
                <option value="18">18</option>
                <option value="19">19</option>
                <option value="20">20</option>
                <option value="21">21</option>
                <option value="22">22</option>
                <option value="23">23</option>
                <option value="24">24</option>
                <option value="25">25</option>
                <option value="26">26</option>
                <option value="27">27</option>
                <option value="28">28</option>
                <option value="29">29</option>
                <option value="30">30</option>
                <option value="31">31</option>
            </select>

            <select name="date_month" id="id_date_month">
                <option value="">---</option>
                <option value="1">januari</option>
                <option value="2">februari</option>
                <option value="3">maart</option>
                <option value="4">april</option>
                <option value="5">mei</option>
                <option value="6">juni</option>
                <option value="7">juli</option>
                <option value="8" selected>augustus</option>
                <option value="9">september</option>
                <option value="10">oktober</option>
                <option value="11">november</option>
                <option value="12">december</option>
            </select>

            <select name="date_year" id="id_date_year">
                <option value="">---</option>
                <option value="2007">2007</option>
                <option value="2008">2008</option>
                <option value="2009">2009</option>
                <option value="2010" selected>2010</option>
                <option value="2011">2011</option>
                <option value="2012">2012</option>
                <option value="2013">2013</option>
                <option value="2014">2014</option>
                <option value="2015">2015</option>
                <option value="2016">2016</option>
            </select>
            """,
        )

        # Even with an invalid date, the widget should reflect the entered value (#17401).
        self.assertEqual(w.render('mydate', '2010-02-30').count('selected'), 3)

        # Years before 1900 should work.
        w = SelectDateWidget(years=('1899',))
        self.assertEqual(
            w.value_from_datadict({'date_year': '1899', 'date_month': '8', 'date_day': '13'}, {}, 'date'),
            '13-08-1899',
        )
        # And years before 1000 (demonstrating the need for datetime_safe).
        w = SelectDateWidget(years=('0001',))
        self.assertEqual(
            w.value_from_datadict({'date_year': '0001', 'date_month': '8', 'date_day': '13'}, {}, 'date'),
            '13-08-0001',
        )

    @override_settings(USE_L10N=False, DATE_INPUT_FORMATS=['%d.%m.%Y'])
    def test_custom_input_format(self):
        w = SelectDateWidget(years=('0001', '1899', '2009', '2010'))
        for values, expected in (
            (('0001', '8', '13'), '13.08.0001'),
            (('1899', '7', '11'), '11.07.1899'),
            (('2009', '3', '7'), '07.03.2009'),
        ):
            with self.subTest(values=values):
                data = {
                    'field_%s' % field: value
                    for field, value in zip(('year', 'month', 'day'), values)
                }
                self.assertEqual(w.value_from_datadict(data, {}, 'field'), expected)

    def test_format_value(self):
        valid_formats = [
            '2000-1-1', '2000-10-15', '2000-01-01',
            '2000-01-0', '2000-0-01', '2000-0-0',
            '0-01-01', '0-01-0', '0-0-01', '0-0-0',
        ]
        for value in valid_formats:
            year, month, day = (int(x) or '' for x in value.split('-'))
            with self.subTest(value=value):
                self.assertEqual(self.widget.format_value(value), {'day': day, 'month': month, 'year': year})

        invalid_formats = [
            '2000-01-001', '2000-001-01', '2-01-01', '20-01-01', '200-01-01',
            '20000-01-01',
        ]
        for value in invalid_formats:
            with self.subTest(value=value):
                self.assertEqual(self.widget.format_value(value), {'day': None, 'month': None, 'year': None})

    def test_value_from_datadict(self):
        tests = [
            (('2000', '12', '1'), '2000-12-01'),
            (('', '12', '1'), '0-12-1'),
            (('2000', '', '1'), '2000-0-1'),
            (('2000', '12', ''), '2000-12-0'),
            (('', '', '', ''), None),
            ((None, '12', '1'), None),
            (('2000', None, '1'), None),
            (('2000', '12', None), None),
        ]
        for values, expected in tests:
            with self.subTest(values=values):
                data = {}
                for field_name, value in zip(('year', 'month', 'day'), values):
                    if value is not None:
                        data['field_%s' % field_name] = value
                self.assertEqual(self.widget.value_from_datadict(data, {}, 'field'), expected)

    def test_value_omitted_from_data(self):
        self.assertIs(self.widget.value_omitted_from_data({}, {}, 'field'), True)
        self.assertIs(self.widget.value_omitted_from_data({'field_month': '12'}, {}, 'field'), False)
        self.assertIs(self.widget.value_omitted_from_data({'field_year': '2000'}, {}, 'field'), False)
        self.assertIs(self.widget.value_omitted_from_data({'field_day': '1'}, {}, 'field'), False)
        data = {'field_day': '1', 'field_month': '12', 'field_year': '2000'}
        self.assertIs(self.widget.value_omitted_from_data(data, {}, 'field'), False)

    @override_settings(USE_THOUSAND_SEPARATOR=True, USE_L10N=True)
    def test_years_rendered_without_separator(self):
        widget = SelectDateWidget(years=(2007,))
        self.check_html(widget, 'mydate', '', html=(
            """
            <select name="mydate_month" id="id_mydate_month">
                <option selected value="">---</option>
                <option value="1">January</option>
                <option value="2">February</option>
                <option value="3">March</option>
                <option value="4">April</option>
                <option value="5">May</option>
                <option value="6">June</option>
                <option value="7">July</option>
                <option value="8">August</option>
                <option value="9">September</option>
                <option value="10">October</option>
                <option value="11">November</option>
                <option value="12">December</option>
            </select>
            <select name="mydate_day" id="id_mydate_day">
                <option selected value="">---</option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4">4</option>
                <option value="5">5</option>
                <option value="6">6</option>
                <option value="7">7</option>
                <option value="8">8</option>
                <option value="9">9</option>
                <option value="10">10</option>
                <option value="11">11</option>
                <option value="12">12</option>
                <option value="13">13</option>
                <option value="14">14</option>
                <option value="15">15</option>
                <option value="16">16</option>
                <option value="17">17</option>
                <option value="18">18</option>
                <option value="19">19</option>
                <option value="20">20</option>
                <option value="21">21</option>
                <option value="22">22</option>
                <option value="23">23</option>
                <option value="24">24</option>
                <option value="25">25</option>
                <option value="26">26</option>
                <option value="27">27</option>
                <option value="28">28</option>
                <option value="29">29</option>
                <option value="30">30</option>
                <option value="31">31</option>
            </select>
            <select name="mydate_year" id="id_mydate_year">
                <option selected value="">---</option>
                <option value="2007">2007</option>
            </select>
            """
        ))

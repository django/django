import unittest

from django.utils.termcolors import (
    DARK_PALETTE, DEFAULT_PALETTE, LIGHT_PALETTE, NOCOLOR_PALETTE, PALETTES,
    colorize, parse_color_setting,
)


class TermColorTests(unittest.TestCase):

    def test_empty_string(self):
        self.assertEqual(parse_color_setting(''), (DEFAULT_PALETTE, PALETTES[DEFAULT_PALETTE]))

    def test_simple_palette(self):
        self.assertEqual(parse_color_setting('light'), (LIGHT_PALETTE, PALETTES[LIGHT_PALETTE]))
        self.assertEqual(parse_color_setting('dark'), (DARK_PALETTE, PALETTES[DARK_PALETTE]))
        self.assertEqual(parse_color_setting('nocolor'), (NOCOLOR_PALETTE, None))

    def test_fg(self):
        self.assertEqual(
            parse_color_setting('error=green'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green'}))
        )

    def test_fg_bg(self):
        self.assertEqual(
            parse_color_setting('error=green/blue'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green', 'bg': 'blue'}))
        )

    def test_fg_opts(self):
        self.assertEqual(
            parse_color_setting('error=green,blink'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green', 'opts': ('blink',)}))
        )
        self.assertEqual(
            parse_color_setting('error=green,bold,blink'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green', 'opts': ('blink', 'bold')}))
        )

    def test_fg_bg_opts(self):
        self.assertEqual(
            parse_color_setting('error=green/blue,blink'),
            (NOCOLOR_PALETTE, dict(
                PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green', 'bg': 'blue', 'opts': ('blink',)}))
        )
        self.assertEqual(
            parse_color_setting('error=green/blue,bold,blink'),
            (NOCOLOR_PALETTE, dict(
                PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green', 'bg': 'blue', 'opts': ('blink', 'bold')}))
        )

    def test_override_palette(self):
        self.assertEqual(
            parse_color_setting('light;error=green'),
            (LIGHT_PALETTE, dict(PALETTES[LIGHT_PALETTE], ERROR={'fg': 'green'}))
        )

    def test_override_nocolor(self):
        self.assertEqual(
            parse_color_setting('nocolor;error=green'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green'}))
        )

    def test_reverse_override(self):
        self.assertEqual(parse_color_setting('error=green;light'), (LIGHT_PALETTE, PALETTES[LIGHT_PALETTE]))

    def test_multiple_roles(self):
        self.assertEqual(
            parse_color_setting('error=green;sql_field=blue'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green'}, SQL_FIELD={'fg': 'blue'}))
        )

    def test_override_with_multiple_roles(self):
        self.assertEqual(
            parse_color_setting('light;error=green;sql_field=blue'),
            (LIGHT_PALETTE, dict(PALETTES[LIGHT_PALETTE], ERROR={'fg': 'green'}, SQL_FIELD={'fg': 'blue'}))
        )

    def test_empty_definition(self):
        self.assertEqual(parse_color_setting(';'), (NOCOLOR_PALETTE, None))
        self.assertEqual(parse_color_setting('light;'), (LIGHT_PALETTE, PALETTES[LIGHT_PALETTE]))
        self.assertEqual(parse_color_setting(';;;'), (NOCOLOR_PALETTE, None))

    def test_empty_options(self):
        self.assertEqual(
            parse_color_setting('error=green,'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green'}))
        )
        self.assertEqual(
            parse_color_setting('error=green,,,'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green'}))
        )
        self.assertEqual(
            parse_color_setting('error=green,,blink,,'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green', 'opts': ('blink',)}))
        )

    def test_bad_palette(self):
        self.assertEqual(parse_color_setting('unknown'), (NOCOLOR_PALETTE, None))

    def test_bad_role(self):
        self.assertEqual(parse_color_setting('unknown='), (NOCOLOR_PALETTE, None))
        self.assertEqual(parse_color_setting('unknown=green'), (NOCOLOR_PALETTE, None))
        self.assertEqual(
            parse_color_setting('unknown=green;sql_field=blue'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], SQL_FIELD={'fg': 'blue'}))
        )

    def test_bad_color(self):
        self.assertEqual(parse_color_setting('error='), (NOCOLOR_PALETTE, None))
        self.assertEqual(
            parse_color_setting('error=;sql_field=blue'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], SQL_FIELD={'fg': 'blue'}))
        )
        self.assertEqual(parse_color_setting('error=unknown'), (NOCOLOR_PALETTE, None))
        self.assertEqual(
            parse_color_setting('error=unknown;sql_field=blue'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], SQL_FIELD={'fg': 'blue'}))
        )
        self.assertEqual(
            parse_color_setting('error=green/unknown'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green'}))
        )
        self.assertEqual(
            parse_color_setting('error=green/blue/something'),
            (NOCOLOR_PALETTE, dict(
                PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green', 'bg': 'blue'}))
        )
        self.assertEqual(
            parse_color_setting('error=green/blue/something,blink'),
            (NOCOLOR_PALETTE, dict(
                PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green', 'bg': 'blue', 'opts': ('blink',)}))
        )

    def test_bad_option(self):
        self.assertEqual(
            parse_color_setting('error=green,unknown'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green'}))
        )
        self.assertEqual(
            parse_color_setting('error=green,unknown,blink'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green', 'opts': ('blink',)}))
        )

    def test_role_case(self):
        self.assertEqual(
            parse_color_setting('ERROR=green'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green'}))
        )
        self.assertEqual(
            parse_color_setting('eRrOr=green'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green'}))
        )

    def test_color_case(self):
        self.assertEqual(
            parse_color_setting('error=GREEN'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green'}))
        )
        self.assertEqual(
            parse_color_setting('error=GREEN/BLUE'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green', 'bg': 'blue'}))
        )
        self.assertEqual(
            parse_color_setting('error=gReEn'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green'}))
        )
        self.assertEqual(
            parse_color_setting('error=gReEn/bLuE'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green', 'bg': 'blue'}))
        )

    def test_opts_case(self):
        self.assertEqual(
            parse_color_setting('error=green,BLINK'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green', 'opts': ('blink',)}))
        )
        self.assertEqual(
            parse_color_setting('error=green,bLiNk'),
            (NOCOLOR_PALETTE, dict(PALETTES[NOCOLOR_PALETTE], ERROR={'fg': 'green', 'opts': ('blink',)}))
        )

    def test_colorize_empty_text(self):
        self.assertEqual(colorize(text=None), '\x1b[m\x1b[0m')
        self.assertEqual(colorize(text=''), '\x1b[m\x1b[0m')

        self.assertEqual(colorize(text=None, opts=('noreset')), '\x1b[m')
        self.assertEqual(colorize(text='', opts=('noreset')), '\x1b[m')

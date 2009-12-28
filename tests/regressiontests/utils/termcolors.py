from unittest import TestCase

from django.utils.termcolors import parse_color_setting, PALETTES, DEFAULT_PALETTE, LIGHT_PALETTE, DARK_PALETTE, NOCOLOR_PALETTE

class TermColorTests(TestCase):

    def test_empty_string(self):
        self.assertEquals(parse_color_setting(''), PALETTES[DEFAULT_PALETTE])

    def test_simple_palette(self):
        self.assertEquals(parse_color_setting('light'), PALETTES[LIGHT_PALETTE])
        self.assertEquals(parse_color_setting('dark'), PALETTES[DARK_PALETTE])
        self.assertEquals(parse_color_setting('nocolor'), None)

    def test_fg(self):
        self.assertEquals(parse_color_setting('error=green'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green'}))

    def test_fg_bg(self):
        self.assertEquals(parse_color_setting('error=green/blue'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green', 'bg':'blue'}))

    def test_fg_opts(self):
        self.assertEquals(parse_color_setting('error=green,blink'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green', 'opts': ('blink',)}))
        self.assertEquals(parse_color_setting('error=green,bold,blink'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green', 'opts': ('blink','bold')}))

    def test_fg_bg_opts(self):
        self.assertEquals(parse_color_setting('error=green/blue,blink'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green', 'bg':'blue', 'opts': ('blink',)}))
        self.assertEquals(parse_color_setting('error=green/blue,bold,blink'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green', 'bg':'blue', 'opts': ('blink','bold')}))

    def test_override_palette(self):
        self.assertEquals(parse_color_setting('light;error=green'),
                          dict(PALETTES[LIGHT_PALETTE],
                            ERROR={'fg':'green'}))

    def test_override_nocolor(self):
        self.assertEquals(parse_color_setting('nocolor;error=green'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg': 'green'}))

    def test_reverse_override(self):
        self.assertEquals(parse_color_setting('error=green;light'), PALETTES[LIGHT_PALETTE])

    def test_multiple_roles(self):
        self.assertEquals(parse_color_setting('error=green;sql_field=blue'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green'},
                            SQL_FIELD={'fg':'blue'}))

    def test_override_with_multiple_roles(self):
        self.assertEquals(parse_color_setting('light;error=green;sql_field=blue'),
                          dict(PALETTES[LIGHT_PALETTE],
                            ERROR={'fg':'green'},
                            SQL_FIELD={'fg':'blue'}))

    def test_empty_definition(self):
        self.assertEquals(parse_color_setting(';'), None)
        self.assertEquals(parse_color_setting('light;'), PALETTES[LIGHT_PALETTE])
        self.assertEquals(parse_color_setting(';;;'), None)

    def test_empty_options(self):
        self.assertEquals(parse_color_setting('error=green,'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green'}))
        self.assertEquals(parse_color_setting('error=green,,,'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green'}))
        self.assertEquals(parse_color_setting('error=green,,blink,,'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green', 'opts': ('blink',)}))

    def test_bad_palette(self):
        self.assertEquals(parse_color_setting('unknown'), None)

    def test_bad_role(self):
        self.assertEquals(parse_color_setting('unknown='), None)
        self.assertEquals(parse_color_setting('unknown=green'), None)
        self.assertEquals(parse_color_setting('unknown=green;sql_field=blue'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            SQL_FIELD={'fg':'blue'}))

    def test_bad_color(self):
        self.assertEquals(parse_color_setting('error='), None)
        self.assertEquals(parse_color_setting('error=;sql_field=blue'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            SQL_FIELD={'fg':'blue'}))
        self.assertEquals(parse_color_setting('error=unknown'), None)
        self.assertEquals(parse_color_setting('error=unknown;sql_field=blue'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            SQL_FIELD={'fg':'blue'}))
        self.assertEquals(parse_color_setting('error=green/unknown'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green'}))
        self.assertEquals(parse_color_setting('error=green/blue/something'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green', 'bg': 'blue'}))
        self.assertEquals(parse_color_setting('error=green/blue/something,blink'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green', 'bg': 'blue', 'opts': ('blink',)}))

    def test_bad_option(self):
        self.assertEquals(parse_color_setting('error=green,unknown'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green'}))
        self.assertEquals(parse_color_setting('error=green,unknown,blink'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green', 'opts': ('blink',)}))

    def test_role_case(self):
        self.assertEquals(parse_color_setting('ERROR=green'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green'}))
        self.assertEquals(parse_color_setting('eRrOr=green'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green'}))

    def test_color_case(self):
        self.assertEquals(parse_color_setting('error=GREEN'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green'}))
        self.assertEquals(parse_color_setting('error=GREEN/BLUE'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green', 'bg':'blue'}))

        self.assertEquals(parse_color_setting('error=gReEn'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green'}))
        self.assertEquals(parse_color_setting('error=gReEn/bLuE'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green', 'bg':'blue'}))

    def test_opts_case(self):
        self.assertEquals(parse_color_setting('error=green,BLINK'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green', 'opts': ('blink',)}))

        self.assertEquals(parse_color_setting('error=green,bLiNk'),
                          dict(PALETTES[NOCOLOR_PALETTE],
                            ERROR={'fg':'green', 'opts': ('blink',)}))

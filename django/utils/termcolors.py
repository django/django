"""
termcolors.py
"""

from django.utils import six

color_names = ('black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white')
foreground = {color_names[x]: '3%s' % x for x in range(8)}
background = {color_names[x]: '4%s' % x for x in range(8)}

RESET = '0'
opt_dict = {'bold': '1', 'underscore': '4', 'blink': '5', 'reverse': '7', 'conceal': '8'}


def colorize(text='', opts=(), **kwargs):
    """
    Returns your text, enclosed in ANSI graphics codes.

    Depends on the keyword arguments 'fg' and 'bg', and the contents of
    the opts tuple/list.

    Returns the RESET code if no parameters are given.

    Valid colors:
        'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'

    Valid options:
        'bold'
        'underscore'
        'blink'
        'reverse'
        'conceal'
        'noreset' - string will not be auto-terminated with the RESET code

    Examples:
        colorize('hello', fg='red', bg='blue', opts=('blink',))
        colorize()
        colorize('goodbye', opts=('underscore',))
        print(colorize('first line', fg='red', opts=('noreset',)))
        print('this should be red too')
        print(colorize('and so should this'))
        print('this should not be red')
    """
    code_list = []
    if text == '' and len(opts) == 1 and opts[0] == 'reset':
        return '\x1b[%sm' % RESET
    for k, v in six.iteritems(kwargs):
        if k == 'fg':
            code_list.append(foreground[v])
        elif k == 'bg':
            code_list.append(background[v])
    for o in opts:
        if o in opt_dict:
            code_list.append(opt_dict[o])
    if 'noreset' not in opts:
        text = '%s\x1b[%sm' % (text or '', RESET)
    return '%s%s' % (('\x1b[%sm' % ';'.join(code_list)), text or '')


def make_style(opts=(), **kwargs):
    """
    Returns a function with default parameters for colorize()

    Example:
        bold_red = make_style(opts=('bold',), fg='red')
        print(bold_red('hello'))
        KEYWORD = make_style(fg='yellow')
        COMMENT = make_style(fg='blue', opts=('bold',))
    """
    return lambda text: colorize(text, opts, **kwargs)

NOCOLOR_PALETTE = 'nocolor'
DARK_PALETTE = 'dark'
LIGHT_PALETTE = 'light'

PALETTES = {
    NOCOLOR_PALETTE: {
        'ERROR': {},
        'WARNING': {},
        'NOTICE': {},
        'SQL_FIELD': {},
        'SQL_COLTYPE': {},
        'SQL_KEYWORD': {},
        'SQL_TABLE': {},
        'HTTP_INFO': {},
        'HTTP_SUCCESS': {},
        'HTTP_REDIRECT': {},
        'HTTP_NOT_MODIFIED': {},
        'HTTP_BAD_REQUEST': {},
        'HTTP_NOT_FOUND': {},
        'HTTP_SERVER_ERROR': {},
        'MIGRATE_HEADING': {},
        'MIGRATE_LABEL': {},
        'MIGRATE_SUCCESS': {},
        'MIGRATE_FAILURE': {},
    },
    DARK_PALETTE: {
        'ERROR': {'fg': 'red', 'opts': ('bold',)},
        'WARNING': {'fg': 'yellow', 'opts': ('bold',)},
        'NOTICE': {'fg': 'red'},
        'SQL_FIELD': {'fg': 'green', 'opts': ('bold',)},
        'SQL_COLTYPE': {'fg': 'green'},
        'SQL_KEYWORD': {'fg': 'yellow'},
        'SQL_TABLE': {'opts': ('bold',)},
        'HTTP_INFO': {'opts': ('bold',)},
        'HTTP_SUCCESS': {},
        'HTTP_REDIRECT': {'fg': 'green'},
        'HTTP_NOT_MODIFIED': {'fg': 'cyan'},
        'HTTP_BAD_REQUEST': {'fg': 'red', 'opts': ('bold',)},
        'HTTP_NOT_FOUND': {'fg': 'yellow'},
        'HTTP_SERVER_ERROR': {'fg': 'magenta', 'opts': ('bold',)},
        'MIGRATE_HEADING': {'fg': 'cyan', 'opts': ('bold',)},
        'MIGRATE_LABEL': {'opts': ('bold',)},
        'MIGRATE_SUCCESS': {'fg': 'green', 'opts': ('bold',)},
        'MIGRATE_FAILURE': {'fg': 'red', 'opts': ('bold',)},
    },
    LIGHT_PALETTE: {
        'ERROR': {'fg': 'red', 'opts': ('bold',)},
        'WARNING': {'fg': 'yellow', 'opts': ('bold',)},
        'NOTICE': {'fg': 'red'},
        'SQL_FIELD': {'fg': 'green', 'opts': ('bold',)},
        'SQL_COLTYPE': {'fg': 'green'},
        'SQL_KEYWORD': {'fg': 'blue'},
        'SQL_TABLE': {'opts': ('bold',)},
        'HTTP_INFO': {'opts': ('bold',)},
        'HTTP_SUCCESS': {},
        'HTTP_REDIRECT': {'fg': 'green', 'opts': ('bold',)},
        'HTTP_NOT_MODIFIED': {'fg': 'green'},
        'HTTP_BAD_REQUEST': {'fg': 'red', 'opts': ('bold',)},
        'HTTP_NOT_FOUND': {'fg': 'red'},
        'HTTP_SERVER_ERROR': {'fg': 'magenta', 'opts': ('bold',)},
        'MIGRATE_HEADING': {'fg': 'cyan', 'opts': ('bold',)},
        'MIGRATE_LABEL': {'opts': ('bold',)},
        'MIGRATE_SUCCESS': {'fg': 'green', 'opts': ('bold',)},
        'MIGRATE_FAILURE': {'fg': 'red', 'opts': ('bold',)},
    }
}
DEFAULT_PALETTE = DARK_PALETTE


def parse_color_setting(config_string):
    """Parse a DJANGO_COLORS environment variable to produce the system palette

    The general form of a pallete definition is:

        "palette;role=fg;role=fg/bg;role=fg,option,option;role=fg/bg,option,option"

    where:
        palette is a named palette; one of 'light', 'dark', or 'nocolor'.
        role is a named style used by Django
        fg is a background color.
        bg is a background color.
        option is a display options.

    Specifying a named palette is the same as manually specifying the individual
    definitions for each role. Any individual definitions following the pallete
    definition will augment the base palette definition.

    Valid roles:
        'error', 'notice', 'sql_field', 'sql_coltype', 'sql_keyword', 'sql_table',
        'http_info', 'http_success', 'http_redirect', 'http_bad_request',
        'http_not_found', 'http_server_error'

    Valid colors:
        'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'

    Valid options:
        'bold', 'underscore', 'blink', 'reverse', 'conceal'

    """
    if not config_string:
        return PALETTES[DEFAULT_PALETTE]

    # Split the color configuration into parts
    parts = config_string.lower().split(';')
    palette = PALETTES[NOCOLOR_PALETTE].copy()
    for part in parts:
        if part in PALETTES:
            # A default palette has been specified
            palette.update(PALETTES[part])
        elif '=' in part:
            # Process a palette defining string
            definition = {}

            # Break the definition into the role,
            # plus the list of specific instructions.
            # The role must be in upper case
            role, instructions = part.split('=')
            role = role.upper()

            styles = instructions.split(',')
            styles.reverse()

            # The first instruction can contain a slash
            # to break apart fg/bg.
            colors = styles.pop().split('/')
            colors.reverse()
            fg = colors.pop()
            if fg in color_names:
                definition['fg'] = fg
            if colors and colors[-1] in color_names:
                definition['bg'] = colors[-1]

            # All remaining instructions are options
            opts = tuple(s for s in styles if s in opt_dict.keys())
            if opts:
                definition['opts'] = opts

            # The nocolor palette has all available roles.
            # Use that palette as the basis for determining
            # if the role is valid.
            if role in PALETTES[NOCOLOR_PALETTE] and definition:
                palette[role] = definition

    # If there are no colors specified, return the empty palette.
    if palette == PALETTES[NOCOLOR_PALETTE]:
        return None
    return palette

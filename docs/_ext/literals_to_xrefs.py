"""
Runs through a reST file looking for old-style literals, and helps replace them
with new-style references.
"""

import re
import sys
import shelve

refre = re.compile(r'``([^`\s]+?)``')

ROLES = (
    'attr',
    'class',
    "djadmin",
    'data',
    'exc',
    'file',
    'func',
    'lookup',
    'meth',
    'mod' ,
    "djadminopt",
    "ref",
    "setting",
    "term",
    "tfilter",
    "ttag",
    
    # special
    "skip"
)

ALWAYS_SKIP = [
    "NULL",
    "True",
    "False",
]

def fixliterals(fname):
    with open(fname) as fp:
        data = fp.read()
    
    last = 0
    new = []
    storage = shelve.open("/tmp/literals_to_xref.shelve")
    lastvalues = storage.get("lastvalues", {})
    
    for m in refre.finditer(data):
        
        new.append(data[last:m.start()])
        last = m.end()
        
        line_start = data.rfind("\n", 0, m.start())
        line_end = data.find("\n", m.end())
        prev_start = data.rfind("\n", 0, line_start)
        next_end = data.find("\n", line_end + 1)
        
        # Skip always-skip stuff
        if m.group(1) in ALWAYS_SKIP:
            new.append(m.group(0))
            continue
            
        # skip when the next line is a title
        next_line = data[m.end():next_end].strip()
        if next_line[0] in "!-/:-@[-`{-~" and all(c == next_line[0] for c in next_line):
            new.append(m.group(0))
            continue
        
        sys.stdout.write("\n"+"-"*80+"\n")
        sys.stdout.write(data[prev_start+1:m.start()])
        sys.stdout.write(colorize(m.group(0), fg="red"))
        sys.stdout.write(data[m.end():next_end])
        sys.stdout.write("\n\n")
        
        replace_type = None
        while replace_type is None:
            replace_type = raw_input(
                colorize("Replace role: ", fg="yellow")
            ).strip().lower()
            if replace_type and replace_type not in ROLES:
                replace_type = None
        
        if replace_type == "":
            new.append(m.group(0))
            continue
            
        if replace_type == "skip":
            new.append(m.group(0))
            ALWAYS_SKIP.append(m.group(1))
            continue
        
        default = lastvalues.get(m.group(1), m.group(1))
        if default.endswith("()") and replace_type in ("class", "func", "meth"):
            default = default[:-2]        
        replace_value = raw_input(
            colorize("Text <target> [", fg="yellow") + default + colorize("]: ", fg="yellow")
        ).strip()
        if not replace_value: 
            replace_value = default
        new.append(":%s:`%s`" % (replace_type, replace_value))
        lastvalues[m.group(1)] = replace_value
    
    new.append(data[last:])
    with open(fname, "w") as fp:
        fp.write("".join(new))
    
    storage["lastvalues"] = lastvalues
    storage.close()
    
#
# The following is taken from django.utils.termcolors and is copied here to
# avoid the dependency.
#


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
    color_names = ('black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white')
    foreground = dict([(color_names[x], '3%s' % x) for x in range(8)])
    background = dict([(color_names[x], '4%s' % x) for x in range(8)])

    RESET = '0'
    opt_dict = {'bold': '1', 'underscore': '4', 'blink': '5', 'reverse': '7', 'conceal': '8'}

    text = str(text)
    code_list = []
    if text == '' and len(opts) == 1 and opts[0] == 'reset':
        return '\x1b[%sm' % RESET
    for k, v in kwargs.iteritems():
        if k == 'fg':
            code_list.append(foreground[v])
        elif k == 'bg':
            code_list.append(background[v])
    for o in opts:
        if o in opt_dict:
            code_list.append(opt_dict[o])
    if 'noreset' not in opts:
        text = text + '\x1b[%sm' % RESET
    return ('\x1b[%sm' % ';'.join(code_list)) + text

if __name__ == '__main__':
    try:
        fixliterals(sys.argv[1])
    except (KeyboardInterrupt, SystemExit):
        print('')

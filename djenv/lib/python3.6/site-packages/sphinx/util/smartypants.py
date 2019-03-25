# -*- coding: utf-8 -*-
"""
    sphinx.util.smartypants
    ~~~~~~~~~~~~~~~~~~~~~~~

    This is extracted (with minor adaptations for flake8 compliance) from
    docutils’ docutils/utils/smartquotes.py as of revision 8097 (30 May 2017),
    in order to backport for Sphinx usage with Docutils < 0.14 extra language
    configurations and fixes. Replaces earlier smartypants version as used up
    to Sphinx 1.5.6.

    :copyright: © 2010 Günter Milde,
                original `SmartyPants`_: © 2003 John Gruber
                smartypants.py:          © 2004, 2007 Chad Miller
    :license: Released under the terms of the `2-Clause BSD license`_, in short:

       Copying and distribution of this file, with or without modification,
       are permitted in any medium without royalty provided the copyright
       notices and this notice are preserved.
       This file is offered as-is, without any warranty.

    .. _SmartyPants: https://daringfireball.net/projects/smartypants/
    .. _2-Clause BSD license: https://spdx.org/licenses/BSD-2-Clause

    See the LICENSE file and the original docutils code for details.

"""
from __future__ import absolute_import, unicode_literals

import re

from docutils.utils import smartquotes

from sphinx.util.docutils import __version_info__ as docutils_version

if False:  # For type annotation
    from typing import Iterable, Iterator, Tuple  # NOQA


langquotes = {'af':           u'“”‘’',
              'af-x-altquot': u'„”‚’',
              'bg':           u'„“‚‘',  # Bulgarian, https://bg.wikipedia.org/wiki/Кавички
              'ca':           u'«»“”',
              'ca-x-altquot': u'“”‘’',
              'cs':           u'„“‚‘',
              'cs-x-altquot': u'»«›‹',
              'da':           u'»«›‹',
              'da-x-altquot': u'„“‚‘',
              # 'da-x-altquot2': u'””’’',
              'de':           u'„“‚‘',
              'de-x-altquot': u'»«›‹',
              'de-ch':        u'«»‹›',
              'el':           u'«»“”',
              'en':           u'“”‘’',
              'en-uk-x-altquot': u'‘’“”',  # Attention: " → ‘ and ' → “ !
              'eo':           u'“”‘’',
              'es':           u'«»“”',
              'es-x-altquot': u'“”‘’',
              'et':           u'„“‚‘',  # no secondary quote listed in
              'et-x-altquot': u'«»‹›',  # the sources above (wikipedia.org)
              'eu':           u'«»‹›',
              'fi':           u'””’’',
              'fi-x-altquot': u'»»››',
              'fr':           (u'« ', u' »', u'“', u'”'),  # full no-break space
              'fr-x-altquot': (u'« ', u' »', u'“', u'”'),  # narrow no-break space
              'fr-ch':        u'«»‹›',
              'fr-ch-x-altquot': (u'« ',  u' »', u'‹ ', u' ›'),  # narrow no-break space
              # http://typoguide.ch/
              'gl':           u'«»“”',
              'he':           u'”“»«',  # Hebrew is RTL, test position:
              'he-x-altquot': u'„”‚’',  # low quotation marks are opening.
              # 'he-x-altquot': u'“„‘‚',  # RTL: low quotation marks opening
              'hr':           u'„”‘’',  # https://hrvatska-tipografija.com/polunavodnici/
              'hr-x-altquot': u'»«›‹',
              'hsb':          u'„“‚‘',
              'hsb-x-altquot': u'»«›‹',
              'hu':           u'„”«»',
              'is':           u'„“‚‘',
              'it':           u'«»“”',
              'it-ch':        u'«»‹›',
              'it-x-altquot': u'“”‘’',
              # 'it-x-altquot2': u'“„‘‚',  # [7] in headlines
              'ja':           u'「」『』',
              'lt':           u'„“‚‘',
              'lv':           u'„“‚‘',
              'mk':           u'„“‚‘',  # Macedonian,
              # https://mk.wikipedia.org/wiki/Правопис_и_правоговор_на_македонскиот_јазик
              'nl':           u'“”‘’',
              'nl-x-altquot': u'„”‚’',
              # 'nl-x-altquot2': u'””’’',
              'nb':           u'«»’’',  # Norsk bokmål (canonical form 'no')
              'nn':           u'«»’’',  # Nynorsk [10]
              'nn-x-altquot': u'«»‘’',  # [8], [10]
              # 'nn-x-altquot2': u'«»«»',  # [9], [10]
              # 'nn-x-altquot3': u'„“‚‘',  # [10]
              'no':           u'«»’’',  # Norsk bokmål [10]
              'no-x-altquot': u'«»‘’',  # [8], [10]
              # 'no-x-altquot2': u'«»«»',  # [9], [10]
              # 'no-x-altquot3': u'„“‚‘',  # [10]
              'pl':           u'„”«»',
              'pl-x-altquot': u'«»‚’',
              # 'pl-x-altquot2': u'„”‚’',
              # https://pl.wikipedia.org/wiki/Cudzys%C5%82%C3%B3w
              'pt':           u'«»“”',
              'pt-br':        u'“”‘’',
              'ro':           u'„”«»',
              'ru':           u'«»„“',
              'sh':           u'„”‚’',  # Serbo-Croatian
              'sh-x-altquot': u'»«›‹',
              'sk':           u'„“‚‘',  # Slovak
              'sk-x-altquot': u'»«›‹',
              'sl':           u'„“‚‘',  # Slovenian
              'sl-x-altquot': u'»«›‹',
              'sq':           u'«»‹›',  # Albanian
              'sq-x-altquot': u'“„‘‚',
              'sr':           u'„”’’',
              'sr-x-altquot': u'»«›‹',
              'sv':           u'””’’',
              'sv-x-altquot': u'»»››',
              'tr':           u'“”‘’',
              'tr-x-altquot': u'«»‹›',
              # 'tr-x-altquot2': u'“„‘‚',  # [7] antiquated?
              'uk':           u'«»„“',
              'uk-x-altquot': u'„“‚‘',
              'zh-cn':        u'“”‘’',
              'zh-tw':        u'「」『』',
              }


def educateQuotes(text, language='en'):
    # type: (unicode, unicode) -> unicode
    """
    Parameter:  - text string (unicode or bytes).
                - language (`BCP 47` language tag.)
    Returns:    The `text`, with "educated" curly quote characters.

    Example input:  "Isn't this fun?"
    Example output: “Isn’t this fun?“;
    """

    smart = smartquotes.smartchars(language)
    try:
        apostrophe = smart.apostrophe
    except Exception:
        apostrophe = u'’'

    # oldtext = text
    punct_class = r"""[!"#\$\%'()*+,-.\/:;<=>?\@\[\\\]\^_`{|}~]"""

    # Special case if the very first character is a quote
    # followed by punctuation at a non-word-break.
    # Close the quotes by brute force:
    text = re.sub(r"""^'(?=%s\\B)""" % (punct_class,), smart.csquote, text)
    text = re.sub(r"""^"(?=%s\\B)""" % (punct_class,), smart.cpquote, text)

    # Special case for double sets of quotes, e.g.:
    #   <p>He said, "'Quoted' words in a larger quote."</p>
    text = re.sub(r""""'(?=\w)""", smart.opquote + smart.osquote, text)
    text = re.sub(r"""'"(?=\w)""", smart.osquote + smart.opquote, text)

    # Special case for decade abbreviations (the '80s):
    if language.startswith('en'):  # TODO similar cases in other languages?
        text = re.sub(r"""'(?=\d{2}s)""", apostrophe, text, re.UNICODE)

    close_class = r"""[^\ \t\r\n\[\{\(\-]"""
    dec_dashes = r"""&#8211;|&#8212;"""

    # Get most opening single quotes:
    opening_single_quotes_regex = re.compile(r"""
                    (
                            \s          |   # a whitespace char, or
                            &nbsp;      |   # a non-breaking space entity, or
                            --          |   # dashes, or
                            &[mn]dash;  |   # named dash entities
                            %s          |   # or decimal entities
                            &\#x201[34];    # or hex
                    )
                    '                 # the quote
                    (?=\w)            # followed by a word character
                    """ % (dec_dashes,), re.VERBOSE | re.UNICODE)
    text = opening_single_quotes_regex.sub(r'\1' + smart.osquote, text)

    # In many locales, single closing quotes are different from apostrophe:
    if smart.csquote != apostrophe:
        apostrophe_regex = re.compile(r"(?<=(\w|\d))'(?=\w)", re.UNICODE)
        text = apostrophe_regex.sub(apostrophe, text)
    # TODO: keep track of quoting level to recognize apostrophe in, e.g.,
    # "Ich fass' es nicht."

    closing_single_quotes_regex = re.compile(r"""
                    (%s)
                    '
                    (?!\s  |       # whitespace
                       s\b |
                        \d         # digits   ('80s)
                    )
                    """ % (close_class,), re.VERBOSE | re.UNICODE)
    text = closing_single_quotes_regex.sub(r'\1' + smart.csquote, text)

    closing_single_quotes_regex = re.compile(r"""
                    (%s)
                    '
                    (\s | s\b)
                    """ % (close_class,), re.VERBOSE | re.UNICODE)
    text = closing_single_quotes_regex.sub(r'\1%s\2' % smart.csquote, text)

    # Any remaining single quotes should be opening ones:
    text = re.sub(r"""'""", smart.osquote, text)

    # Get most opening double quotes:
    opening_double_quotes_regex = re.compile(r"""
                    (
                            \s          |   # a whitespace char, or
                            &nbsp;      |   # a non-breaking space entity, or
                            --          |   # dashes, or
                            &[mn]dash;  |   # named dash entities
                            %s          |   # or decimal entities
                            &\#x201[34];    # or hex
                    )
                    "                 # the quote
                    (?=\w)            # followed by a word character
                    """ % (dec_dashes,), re.VERBOSE)
    text = opening_double_quotes_regex.sub(r'\1' + smart.opquote, text)

    # Double closing quotes:
    closing_double_quotes_regex = re.compile(r"""
                    #(%s)?   # character that indicates the quote should be closing
                    "
                    (?=\s)
                    """ % (close_class,), re.VERBOSE)
    text = closing_double_quotes_regex.sub(smart.cpquote, text)

    closing_double_quotes_regex = re.compile(r"""
                    (%s)   # character that indicates the quote should be closing
                    "
                    """ % (close_class,), re.VERBOSE)
    text = closing_double_quotes_regex.sub(r'\1' + smart.cpquote, text)

    # Any remaining quotes should be opening ones.
    text = re.sub(r'"', smart.opquote, text)

    return text


def educate_tokens(text_tokens, attr=smartquotes.default_smartypants_attr, language='en'):
    # type: (Iterable[Tuple[str, unicode]], unicode, unicode) -> Iterator
    """Return iterator that "educates" the items of `text_tokens`.

    This is modified to intercept the ``attr='2'`` as it was used by the
    Docutils 0.13.1 SmartQuotes transform in a hard coded way. Docutils 0.14
    uses ``'qDe'``` and is configurable, and its choice is backported here
    for use by Sphinx with earlier Docutils releases. Similarly ``'1'`` is
    replaced by ``'qde'``.

    Use ``attr='qDbe'``, resp. ``'qdbe'`` to recover Docutils effect of ``'2'``,
    resp. ``'1'``.

    refs: https://sourceforge.net/p/docutils/mailman/message/35869025/
    """

    # Parse attributes:
    # 0 : do nothing
    # 1 : set all (but backticks)
    # 2 : set all (but backticks), using old school en- and em- dash shortcuts
    # 3 : set all, using inverted old school en and em- dash shortcuts
    #
    # q : quotes
    # b : backtick quotes (``double'' only)
    # B : backtick quotes (``double'' and `single')
    # d : dashes
    # D : old school dashes
    # i : inverted old school dashes
    # e : ellipses
    # w : convert &quot; entities to " for Dreamweaver users

    convert_quot = False  # translate &quot; entities into normal quotes?
    do_dashes = 0
    do_backticks = 0
    do_quotes = False
    do_ellipses = False
    do_stupefy = False

    if attr == "1":  # Do everything, turn all options on.
        do_quotes = True
        # do_backticks = 1
        do_dashes = 1
        do_ellipses = True
    elif attr == "2":
        # Do everything, turn all options on, use old school dash shorthand.
        do_quotes = True
        # do_backticks = 1
        do_dashes = 2
        do_ellipses = True
    elif attr == "3":
        # Do everything, use inverted old school dash shorthand.
        do_quotes = True
        do_backticks = 1
        do_dashes = 3
        do_ellipses = True
    elif attr == "-1":  # Special "stupefy" mode.
        do_stupefy = True
    else:
        if "q" in attr:
            do_quotes = True
        if "b" in attr:
            do_backticks = 1
        if "B" in attr:
            do_backticks = 2
        if "d" in attr:
            do_dashes = 1
        if "D" in attr:
            do_dashes = 2
        if "i" in attr:
            do_dashes = 3
        if "e" in attr:
            do_ellipses = True
        if "w" in attr:
            convert_quot = True

    prev_token_last_char = " "
    # Last character of the previous text token. Used as
    # context to curl leading quote characters correctly.

    for (ttype, text) in text_tokens:

        # skip HTML and/or XML tags as well as emtpy text tokens
        # without updating the last character
        if ttype == 'tag' or not text:
            yield text
            continue

        # skip literal text (math, literal, raw, ...)
        if ttype == 'literal':
            prev_token_last_char = text[-1:]
            yield text
            continue

        last_char = text[-1:]  # Remember last char before processing.

        text = smartquotes.processEscapes(text)

        if convert_quot:
            text = re.sub('&quot;', '"', text)

        if do_dashes == 1:
            text = smartquotes.educateDashes(text)
        elif do_dashes == 2:
            text = smartquotes.educateDashesOldSchool(text)
        elif do_dashes == 3:
            text = smartquotes.educateDashesOldSchoolInverted(text)

        if do_ellipses:
            text = smartquotes.educateEllipses(text)

        # Note: backticks need to be processed before quotes.
        if do_backticks:
            text = smartquotes.educateBackticks(text, language)

        if do_backticks == 2:
            text = smartquotes.educateSingleBackticks(text, language)

        if do_quotes:
            # Replace plain quotes to prevent converstion to
            # 2-character sequence in French.
            context = prev_token_last_char.replace('"', ';').replace("'", ';')
            text = educateQuotes(context + text, language)[1:]

        if do_stupefy:
            text = smartquotes.stupefyEntities(text, language)

        # Remember last char as context for the next token
        prev_token_last_char = last_char

        text = smartquotes.processEscapes(text, restore=True)

        yield text


if docutils_version < (0, 13, 2):
    # Monkey patch the old docutils versions to fix the issues mentioned
    # at https://sourceforge.net/p/docutils/bugs/313/
    # at https://sourceforge.net/p/docutils/bugs/317/
    # and more
    smartquotes.educateQuotes = educateQuotes
    smartquotes.educate_tokens = educate_tokens

    # Fix the issue with French quotes mentioned at
    # https://sourceforge.net/p/docutils/mailman/message/35760696/
    # Add/fix other languages as well
    smartquotes.smartchars.quotes = langquotes

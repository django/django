#! /usr/bin/env python3
# :Id: $Id: smartquotes.py 10136 2025-05-20 15:48:27Z milde $
# :Copyright: © 2010-2023 Günter Milde,
#             original `SmartyPants`_: © 2003 John Gruber
#             smartypants.py:          © 2004, 2007 Chad Miller
# :Maintainer: docutils-develop@lists.sourceforge.net
# :License: Released under the terms of the `2-Clause BSD license`_, in short:
#
#    Copying and distribution of this file, with or without modification,
#    are permitted in any medium without royalty provided the copyright
#    notices and this notice are preserved.
#    This file is offered as-is, without any warranty.
#
# .. _2-Clause BSD license: https://opensource.org/licenses/BSD-2-Clause


r"""
=========================
Smart Quotes for Docutils
=========================

Synopsis
========

"SmartyPants" is a free web publishing plug-in for Movable Type, Blosxom, and
BBEdit that easily translates plain ASCII punctuation characters into "smart"
typographic punctuation characters.

``smartquotes.py`` is an adaption of "SmartyPants" to Docutils_.

* Using Unicode instead of HTML entities for typographic punctuation
  characters, it works for any output format that supports Unicode.
* Supports `language specific quote characters`__.

__ https://en.wikipedia.org/wiki/Non-English_usage_of_quotation_marks


Authors
=======

`John Gruber`_ did all of the hard work of writing this software in Perl for
`Movable Type`_ and almost all of this useful documentation.  `Chad Miller`_
ported it to Python to use with Pyblosxom_.
Adapted to Docutils_ by Günter Milde.

Additional Credits
==================

Portions of the SmartyPants original work are based on Brad Choate's nifty
MTRegex plug-in.  `Brad Choate`_ also contributed a few bits of source code to
this plug-in.  Brad Choate is a fine hacker indeed.

`Jeremy Hedley`_ and `Charles Wiltgen`_ deserve mention for exemplary beta
testing of the original SmartyPants.

`Rael Dornfest`_ ported SmartyPants to Blosxom.

.. _Brad Choate: http://bradchoate.com/
.. _Jeremy Hedley: http://antipixel.com/
.. _Charles Wiltgen: http://playbacktime.com/
.. _Rael Dornfest: http://raelity.org/


Copyright and License
=====================

SmartyPants_ license (3-Clause BSD license):

  Copyright (c) 2003 John Gruber (http://daringfireball.net/)
  All rights reserved.

  Redistribution and use in source and binary forms, with or without
  modification, are permitted provided that the following conditions are
  met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in
    the documentation and/or other materials provided with the
    distribution.

  * Neither the name "SmartyPants" nor the names of its contributors
    may be used to endorse or promote products derived from this
    software without specific prior written permission.

  This software is provided by the copyright holders and contributors
  "as is" and any express or implied warranties, including, but not
  limited to, the implied warranties of merchantability and fitness for
  a particular purpose are disclaimed. In no event shall the copyright
  owner or contributors be liable for any direct, indirect, incidental,
  special, exemplary, or consequential damages (including, but not
  limited to, procurement of substitute goods or services; loss of use,
  data, or profits; or business interruption) however caused and on any
  theory of liability, whether in contract, strict liability, or tort
  (including negligence or otherwise) arising in any way out of the use
  of this software, even if advised of the possibility of such damage.

smartypants.py license (2-Clause BSD license):

  smartypants.py is a derivative work of SmartyPants.

  Redistribution and use in source and binary forms, with or without
  modification, are permitted provided that the following conditions are
  met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in
    the documentation and/or other materials provided with the
    distribution.

  This software is provided by the copyright holders and contributors
  "as is" and any express or implied warranties, including, but not
  limited to, the implied warranties of merchantability and fitness for
  a particular purpose are disclaimed. In no event shall the copyright
  owner or contributors be liable for any direct, indirect, incidental,
  special, exemplary, or consequential damages (including, but not
  limited to, procurement of substitute goods or services; loss of use,
  data, or profits; or business interruption) however caused and on any
  theory of liability, whether in contract, strict liability, or tort
  (including negligence or otherwise) arising in any way out of the use
  of this software, even if advised of the possibility of such damage.

.. _John Gruber: http://daringfireball.net/
.. _Chad Miller: http://web.chad.org/

.. _Pyblosxom: http://pyblosxom.bluesock.org/
.. _SmartyPants: http://daringfireball.net/projects/smartypants/
.. _Movable Type: http://www.movabletype.org/
.. _2-Clause BSD license: https://opensource.org/licenses/BSD-2-Clause
.. _Docutils: https://docutils.sourceforge.io/

Description
===========

SmartyPants can perform the following transformations:

- Straight quotes ( " and ' ) into "curly" quote characters
- Backticks-style quotes (\`\`like this'') into "curly" quote characters
- Dashes (``--`` and ``---``) into en- and em-dash entities
- Three consecutive dots (``...`` or ``. . .``) into an ellipsis ``…``.

This means you can write, edit, and save your posts using plain old
ASCII straight quotes, plain dashes, and plain dots, but your published
posts (and final HTML output) will appear with smart quotes, em-dashes,
and proper ellipses.

Backslash Escapes
=================

If you need to use literal straight quotes (or plain hyphens and periods),
`smartquotes` accepts the following backslash escape sequences to force
ASCII-punctuation. Mind, that you need two backslashes in "docstrings", as
Python expands them, too.

========  =========
Escape    Character
========  =========
``\\``    \\
``\\"``   \\"
``\\'``   \\'
``\\.``   \\.
``\\-``   \\-
``\\```   \\`
========  =========

This is useful, for example, when you want to use straight quotes as
foot and inch marks: 6\\'2\\" tall; a 17\\" iMac.


Caveats
=======

Why You Might Not Want to Use Smart Quotes in Your Weblog
---------------------------------------------------------

For one thing, you might not care.

Most normal, mentally stable individuals do not take notice of proper
typographic punctuation. Many design and typography nerds, however, break
out in a nasty rash when they encounter, say, a restaurant sign that uses
a straight apostrophe to spell "Joe's".

If you're the sort of person who just doesn't care, you might well want to
continue not caring. Using straight quotes -- and sticking to the 7-bit
ASCII character set in general -- is certainly a simpler way to live.

Even if you *do* care about accurate typography, you still might want to
think twice before educating the quote characters in your weblog. One side
effect of publishing curly quote characters is that it makes your
weblog a bit harder for others to quote from using copy-and-paste. What
happens is that when someone copies text from your blog, the copied text
contains the 8-bit curly quote characters (as well as the 8-bit characters
for em-dashes and ellipses, if you use these options). These characters
are not standard across different text encoding methods, which is why they
need to be encoded as characters.

People copying text from your weblog, however, may not notice that you're
using curly quotes, and they'll go ahead and paste the unencoded 8-bit
characters copied from their browser into an email message or their own
weblog. When pasted as raw "smart quotes", these characters are likely to
get mangled beyond recognition.

That said, my own opinion is that any decent text editor or email client
makes it easy to stupefy smart quote characters into their 7-bit
equivalents, and I don't consider it my problem if you're using an
indecent text editor or email client.


Algorithmic Shortcomings
------------------------

One situation in which quotes will get curled the wrong way is when
apostrophes are used at the start of leading contractions. For example::

  'Twas the night before Christmas.

In the case above, SmartyPants will turn the apostrophe into an opening
secondary quote, when in fact it should be the `RIGHT SINGLE QUOTATION MARK`
character which is also "the preferred character to use for apostrophe"
(Unicode). I don't think this problem can be solved in the general case --
every word processor I've tried gets this wrong as well. In such cases, it's
best to inset the `RIGHT SINGLE QUOTATION MARK` (’) by hand.

In English, the same character is used for apostrophe and  closing secondary
quote (both plain and "smart" ones). For other locales (French, Italean,
Swiss, ...) "smart" secondary closing quotes differ from the curly apostrophe.

   .. class:: language-fr

   Il dit : "C'est 'super' !"

If the apostrophe is used at the end of a word, it cannot be distinguished
from a secondary quote by the algorithm. Therefore, a text like::

   .. class:: language-de-CH

   "Er sagt: 'Ich fass' es nicht.'"

will get a single closing guillemet instead of an apostrophe.

This can be prevented by use use of the `RIGHT SINGLE QUOTATION MARK` in
the source::

   -  "Er sagt: 'Ich fass' es nicht.'"
   +  "Er sagt: 'Ich fass’ es nicht.'"


Version History
===============

1.10    2023-11-18
        - Pre-compile regexps once, not with every call of `educateQuotes()`
          (patch #206 by Chris Sewell). Simplify regexps.

1.9     2022-03-04
        - Code cleanup. Require Python 3.

1.8.1   2017-10-25
        - Use open quote after Unicode whitespace, ZWSP, and ZWNJ.
        - Code cleanup.

1.8:    2017-04-24
        - Command line front-end.

1.7.1:  2017-03-19
        - Update and extend language-dependent quotes.
        - Differentiate apostrophe from single quote.

1.7:    2012-11-19
        - Internationalization: language-dependent quotes.

1.6.1:  2012-11-06
        - Refactor code, code cleanup,
        - `educate_tokens()` generator as interface for Docutils.

1.6:    2010-08-26
        - Adaption to Docutils:
          - Use Unicode instead of HTML entities,
          - Remove code special to pyblosxom.

1.5_1.6: Fri, 27 Jul 2007 07:06:40 -0400
        - Fixed bug where blocks of precious unalterable text was instead
          interpreted.  Thanks to Le Roux and Dirk van Oosterbosch.

1.5_1.5: Sat, 13 Aug 2005 15:50:24 -0400
        - Fix bogus magical quotation when there is no hint that the
          user wants it, e.g., in "21st century".  Thanks to Nathan Hamblen.
        - Be smarter about quotes before terminating numbers in an en-dash'ed
          range.

1.5_1.4: Thu, 10 Feb 2005 20:24:36 -0500
        - Fix a date-processing bug, as reported by jacob childress.
        - Begin a test-suite for ensuring correct output.
        - Removed import of "string", since I didn't really need it.
          (This was my first every Python program.  Sue me!)

1.5_1.3: Wed, 15 Sep 2004 18:25:58 -0400
        - Abort processing if the flavour is in forbidden-list.  Default of
          [ "rss" ]   (Idea of Wolfgang SCHNERRING.)
        - Remove stray virgules from en-dashes.  Patch by Wolfgang SCHNERRING.

1.5_1.2: Mon, 24 May 2004 08:14:54 -0400
        - Some single quotes weren't replaced properly.  Diff-tesuji played
          by Benjamin GEIGER.

1.5_1.1: Sun, 14 Mar 2004 14:38:28 -0500
        - Support upcoming pyblosxom 0.9 plugin verification feature.

1.5_1.0: Tue, 09 Mar 2004 08:08:35 -0500
        - Initial release
"""

from __future__ import annotations

import re
import sys


options = r"""
Options
=======

Numeric values are the easiest way to configure SmartyPants' behavior:

:0:     Suppress all transformations. (Do nothing.)

:1:     Performs default SmartyPants transformations: quotes (including
        \`\`backticks'' -style), em-dashes, and ellipses. "``--``" (dash dash)
        is used to signify an em-dash; there is no support for en-dashes

:2:     Same as smarty_pants="1", except that it uses the old-school typewriter
        shorthand for dashes:  "``--``" (dash dash) for en-dashes, "``---``"
        (dash dash dash)
        for em-dashes.

:3:     Same as smarty_pants="2", but inverts the shorthand for dashes:
        "``--``" (dash dash) for em-dashes, and "``---``" (dash dash dash) for
        en-dashes.

:-1:    Stupefy mode. Reverses the SmartyPants transformation process, turning
        the characters produced by SmartyPants into their ASCII equivalents.
        E.g. the LEFT DOUBLE QUOTATION MARK (“) is turned into a simple
        double-quote (\"), "—" is turned into two dashes, etc.


The following single-character attribute values can be combined to toggle
individual transformations from within the smarty_pants attribute. For
example, ``"1"`` is equivalent to ``"qBde"``.

:q:     Educates normal quote characters: (") and (').

:b:     Educates \`\`backticks'' -style double quotes.

:B:     Educates \`\`backticks'' -style double quotes and \`single' quotes.

:d:     Educates em-dashes.

:D:     Educates em-dashes and en-dashes, using old-school typewriter
        shorthand: (dash dash) for en-dashes, (dash dash dash) for em-dashes.

:i:     Educates em-dashes and en-dashes, using inverted old-school typewriter
        shorthand: (dash dash) for em-dashes, (dash dash dash) for en-dashes.

:e:     Educates ellipses.

:w:     Translates any instance of ``&quot;`` into a normal double-quote
        character. This should be of no interest to most people, but
        of particular interest to anyone who writes their posts using
        Dreamweaver, as Dreamweaver inexplicably uses this entity to represent
        a literal double-quote character. SmartyPants only educates normal
        quotes, not entities (because ordinarily, entities are used for
        the explicit purpose of representing the specific character they
        represent). The "w" option must be used in conjunction with one (or
        both) of the other quote options ("q" or "b"). Thus, if you wish to
        apply all SmartyPants transformations (quotes, en- and em-dashes, and
        ellipses) and also translate ``&quot;`` entities into regular quotes
        so SmartyPants can educate them, you should pass the following to the
        smarty_pants attribute:
"""


class smartchars:
    """Smart quotes and dashes"""

    endash = '–'      # EN DASH
    emdash = '—'      # EM DASH
    ellipsis = '…'    # HORIZONTAL ELLIPSIS
    apostrophe = '’'  # RIGHT SINGLE QUOTATION MARK

    # quote characters (language-specific, set in __init__())
    # https://en.wikipedia.org/wiki/Non-English_usage_of_quotation_marks
    # https://de.wikipedia.org/wiki/Anf%C3%BChrungszeichen#Andere_Sprachen
    # https://fr.wikipedia.org/wiki/Guillemet
    # https://typographisme.net/post/Les-espaces-typographiques-et-le-web
    # https://www.btb.termiumplus.gc.ca/tpv2guides/guides/redac/index-fra.html
    # https://en.wikipedia.org/wiki/Hebrew_punctuation#Quotation_marks
    # [7] https://www.tustep.uni-tuebingen.de/bi/bi00/bi001t1-anfuehrung.pdf
    # [8] https://www.korrekturavdelingen.no/anforselstegn.htm
    # [9] Typografisk håndbok. Oslo: Spartacus. 2000. s. 67. ISBN 8243001530.
    # [10] https://www.typografi.org/sitat/sitatart.html
    # [11] https://mk.wikipedia.org/wiki/Правопис_и_правоговор_на_македонскиот_јазик  # noqa:E501
    # [12] https://hrvatska-tipografija.com/polunavodnici/
    # [13] https://pl.wikipedia.org/wiki/Cudzys%C5%82%C3%B3w
    #
    # See also configuration option "smartquote-locales".
    quotes = {
        'af':           '“”‘’',
        'af-x-altquot': '„”‚’',
        'bg':           '„“‚‘',  # https://bg.wikipedia.org/wiki/Кавички
        'ca':           '«»“”',
        'ca-x-altquot': '“”‘’',
        'cs':           '„“‚‘',
        'cs-x-altquot': '»«›‹',
        'da':           '»«›‹',
        'da-x-altquot': '„“‚‘',
        # 'da-x-altquot2': '””’’',
        'de':           '„“‚‘',
        'de-x-altquot': '»«›‹',
        'de-ch':        '«»‹›',
        'el':           '«»“”',  # '«»‟”' https://hal.science/hal-02101618
        'en':           '“”‘’',
        'en-uk-x-altquot': '‘’“”',  # Attention: " → ‘ and ' → “ !
        'eo':           '“”‘’',
        'es':           '«»“”',
        'es-x-altquot': '“”‘’',
        'et':           '„“‚‘',  # no secondary quote listed in
        'et-x-altquot': '«»‹›',  # the sources above (wikipedia.org)
        'eu':           '«»‹›',
        'fi':           '””’’',
        'fi-x-altquot': '»»››',
        'fr':           ('« ', ' »', '“', '”'),  # full no-break space
        'fr-x-altquot': ('« ', ' »', '“', '”'),  # narrow no-break space
        'fr-ch':        '«»‹›',                  # https://typoguide.ch/
        'fr-ch-x-altquot': ('« ',  ' »', '‹ ', ' ›'),  # narrow no-break space  # noqa:E501
        'gl':           '«»“”',
        'he':           '”“»«',  # Hebrew is RTL, test position:
        'he-x-altquot': '„”‚’',  # low quotation marks are opening.
        # 'he-x-altquot': '“„‘‚',  # RTL: low quotation marks opening
        'hr':           '„”‘’',  # Croatian [12]
        'hr-x-altquot': '»«›‹',
        'hsb':          '„“‚‘',
        'hsb-x-altquot': '»«›‹',
        'hu':           '„”«»',
        'is':           '„“‚‘',
        'it':           '«»“”',
        'it-ch':        '«»‹›',
        'it-x-altquot': '“”‘’',
        # 'it-x-altquot2': '“„‘‚',  # [7] in headlines
        'ja':           '「」『』',
        'ko':           '“”‘’',
        'lt':           '„“‚‘',
        'lv':           '„“‚‘',
        'mk':           '„“‚‘',  # Macedonian [11]
        'nl':           '“”‘’',
        'nl-x-altquot': '„”‚’',
        # 'nl-x-altquot2': '””’’',
        'nb':           '«»’’',     # Norsk bokmål (canonical form 'no')
        'nn':           '«»’’',     # Nynorsk [10]
        'nn-x-altquot': '«»‘’',     # [8], [10]
        # 'nn-x-altquot2': '«»«»',  # [9], [10]
        # 'nn-x-altquot3': '„“‚‘',  # [10]
        'no':           '«»’’',     # Norsk bokmål [10]
        'no-x-altquot': '«»‘’',     # [8], [10]
        # 'no-x-altquot2': '«»«»',  # [9], [10
        # 'no-x-altquot3': '„“‚‘',  # [10]
        'pl':           '„”«»',
        'pl-x-altquot': '«»‚’',
        # 'pl-x-altquot2': '„”‚’',  # [13]
        'pt':           '«»“”',
        'pt-br':        '“”‘’',
        'ro':           '„”«»',
        'ru':           '«»„“',
        'sh':           '„”‚’',  # Serbo-Croatian
        'sh-x-altquot': '»«›‹',
        'sk':           '„“‚‘',  # Slovak
        'sk-x-altquot': '»«›‹',
        'sl':           '„“‚‘',  # Slovenian
        'sl-x-altquot': '»«›‹',
        'sq':           '«»‹›',  # Albanian
        'sq-x-altquot': '“„‘‚',
        'sr':           '„”’’',
        'sr-x-altquot': '»«›‹',
        'sv':           '””’’',
        'sv-x-altquot': '»»››',
        'tr':           '“”‘’',
        'tr-x-altquot': '«»‹›',
        # 'tr-x-altquot2': '“„‘‚',  # [7] antiquated?
        'uk':           '«»„“',
        'uk-x-altquot': '„“‚‘',
        'zh-cn':        '“”‘’',
        'zh-tw':        '「」『』',
        }

    def __init__(self, language='en') -> None:
        self.language = language
        try:
            (self.opquote, self.cpquote,
             self.osquote, self.csquote) = self.quotes[language.lower()]
        except KeyError:
            self.opquote, self.cpquote, self.osquote, self.csquote = '""\'\''


class RegularExpressions:
    # character classes:
    _CH_CLASSES = {'open': '[([{]',    # opening braces
                   'close': r'[^\s]',  # everything except whitespace
                   'punct': r"""[-!"  #\$\%'()*+,.\/:;<=>?\@\[\\\]\^_`{|}~]""",
                   'dash': r'[-–—]',
                   'sep': '[\\s\u200B\u200C]',  # Whitespace, ZWSP, ZWNJ
                   }
    START_SINGLE = re.compile(r"^'(?=%s\\B)" % _CH_CLASSES['punct'])
    START_DOUBLE = re.compile(r'^"(?=%s\\B)' % _CH_CLASSES['punct'])
    ADJACENT_1 = re.compile('"\'(?=\\w)')
    ADJACENT_2 = re.compile('\'"(?=\\w)')
    OPEN_SINGLE = re.compile(r"(%(open)s|%(dash)s)'(?=%(punct)s? )"
                             % _CH_CLASSES)
    OPEN_DOUBLE = re.compile(r'(%(open)s|%(dash)s)"(?=%(punct)s? )'
                             % _CH_CLASSES)
    DECADE = re.compile(r"'(?=\d{2}s)")
    APOSTROPHE = re.compile(r"(?<=(\w|\d))'(?=\w)")
    OPENING_SECONDARY = re.compile("""
                    (# ?<=  # look behind fails: requires fixed-width pattern
                        %(sep)s     |  # a whitespace char, or
                        %(open)s    |  # opening brace, or
                        %(dash)s       # em/en-dash
                    )
                    '                  # the quote
                    (?=\\w|%(punct)s)  # word character or punctuation
                    """ % _CH_CLASSES, re.VERBOSE)
    CLOSING_SECONDARY = re.compile(r"(?<!\s)'")
    OPENING_PRIMARY = re.compile("""
                    (
                        %(sep)s     |  # a whitespace char, or
                        %(open)s    |  # zero width separating char, or
                        %(dash)s       # em/en-dash
                    )
                    "                 # the quote, followed by
                    (?=\\w|%(punct)s) # a word character or punctuation
                    """ % _CH_CLASSES, re.VERBOSE)
    CLOSING_PRIMARY = re.compile(r"""
                    (
                    (?<!\s)" | # no whitespace before
                    "(?=\s)    # whitespace behind
                    )
                    """, re.VERBOSE)


regexes = RegularExpressions()


default_smartypants_attr = '1'


def smartyPants(text, attr=default_smartypants_attr, language='en'):
    """Main function for "traditional" use."""

    return "".join(t for t in educate_tokens(tokenize(text), attr, language))


def educate_tokens(text_tokens, attr=default_smartypants_attr, language='en'):
    """Return iterator that "educates" the items of `text_tokens`."""
    # Parse attributes:
    # 0 : do nothing
    # 1 : set all
    # 2 : set all, using old school en- and em- dash shortcuts
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
    do_dashes = False
    do_backticks = False
    do_quotes = False
    do_ellipses = False
    do_stupefy = False

    # if attr == "0":  # pass tokens unchanged (see below).
    if attr == '1':  # Do everything, turn all options on.
        do_quotes = True
        do_backticks = True
        do_dashes = 1
        do_ellipses = True
    elif attr == '2':
        # Do everything, turn all options on, use old school dash shorthand.
        do_quotes = True
        do_backticks = True
        do_dashes = 2
        do_ellipses = True
    elif attr == '3':
        # Do everything, use inverted old school dash shorthand.
        do_quotes = True
        do_backticks = True
        do_dashes = 3
        do_ellipses = True
    elif attr == '-1':  # Special "stupefy" mode.
        do_stupefy = True
    else:
        if 'q' in attr: do_quotes = True     # noqa: E701
        if 'b' in attr: do_backticks = True  # noqa: E701
        if 'B' in attr: do_backticks = 2     # noqa: E701
        if 'd' in attr: do_dashes = 1        # noqa: E701
        if 'D' in attr: do_dashes = 2        # noqa: E701
        if 'i' in attr: do_dashes = 3        # noqa: E701
        if 'e' in attr: do_ellipses = True   # noqa: E701
        if 'w' in attr: convert_quot = True  # noqa: E701

    prev_token_last_char = ' '
    # Last character of the previous text token. Used as
    # context to curl leading quote characters correctly.

    for (ttype, text) in text_tokens:

        # skip HTML and/or XML tags as well as empty text tokens
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

        text = processEscapes(text)

        if convert_quot:
            text = text.replace('&quot;', '"')

        if do_dashes == 1:
            text = educateDashes(text)
        elif do_dashes == 2:
            text = educateDashesOldSchool(text)
        elif do_dashes == 3:
            text = educateDashesOldSchoolInverted(text)

        if do_ellipses:
            text = educateEllipses(text)

        # Note: backticks need to be processed before quotes.
        if do_backticks:
            text = educateBackticks(text, language)

        if do_backticks == 2:
            text = educateSingleBackticks(text, language)

        if do_quotes:
            # Replace plain quotes in context to prevent conversion to
            # 2-character sequence in French.
            context = prev_token_last_char.replace('"', ';').replace("'", ';')
            text = educateQuotes(context+text, language)[1:]

        if do_stupefy:
            text = stupefyEntities(text, language)

        # Remember last char as context for the next token
        prev_token_last_char = last_char

        text = processEscapes(text, restore=True)

        yield text


def educateQuotes(text, language='en'):
    """
    Parameter:  - text string (unicode or bytes).
                - language (`BCP 47` language tag.)
    Returns:    The `text`, with "educated" curly quote characters.

    Example input:  "Isn't this fun?"
    Example output: “Isn’t this fun?“
    """
    smart = smartchars(language)

    if not re.search('[-"\']', text):
        return text

    # Special case if the very first character is a quote
    # followed by punctuation at a non-word-break. Use closing quotes.
    # TODO: example (when does this match?)
    text = regexes.START_SINGLE.sub(smart.csquote, text)
    text = regexes.START_DOUBLE.sub(smart.cpquote, text)

    # Special case for adjacent quotes
    # like "'Quoted' words in a larger quote."
    text = regexes.ADJACENT_1.sub(smart.opquote+smart.osquote, text)
    text = regexes.ADJACENT_2.sub(smart.osquote+smart.opquote, text)

    # Special case: "opening character" followed by quote,
    # optional punctuation and space like "[", '(', or '-'.
    text = regexes.OPEN_SINGLE.sub(r'\1%s'%smart.csquote, text)
    text = regexes.OPEN_DOUBLE.sub(r'\1%s'%smart.cpquote, text)

    # Special case for decade abbreviations (the '80s):
    if language.startswith('en'):  # TODO similar cases in other languages?
        text = regexes.DECADE.sub(smart.apostrophe, text)

    # Get most opening secondary quotes:
    text = regexes.OPENING_SECONDARY.sub(r'\1'+smart.osquote, text)

    # In many locales, secondary closing quotes are different from apostrophe:
    if smart.csquote != smart.apostrophe:
        text = regexes.APOSTROPHE.sub(smart.apostrophe, text)
    # TODO: keep track of quoting level to recognize apostrophe in, e.g.,
    # "Ich fass' es nicht."

    text = regexes.CLOSING_SECONDARY.sub(smart.csquote, text)

    # Any remaining secondary quotes should be opening ones:
    text = text.replace(r"'", smart.osquote)

    # Get most opening primary quotes:
    text = regexes.OPENING_PRIMARY.sub(r'\1'+smart.opquote, text)

    # primary closing quotes:
    text = regexes.CLOSING_PRIMARY.sub(smart.cpquote, text)

    # Any remaining quotes should be opening ones.
    text = text.replace(r'"', smart.opquote)

    return text


def educateBackticks(text, language='en'):
    """
    Parameter:  String (unicode or bytes).
    Returns:    The `text`, with ``backticks'' -style double quotes
                translated into HTML curly quote entities.
    Example input:  ``Isn't this fun?''
    Example output: “Isn't this fun?“
    """
    smart = smartchars(language)

    text = text.replace(r'``', smart.opquote)
    text = text.replace(r"''", smart.cpquote)
    return text


def educateSingleBackticks(text, language='en'):
    """
    Parameter:  String (unicode or bytes).
    Returns:    The `text`, with `backticks' -style single quotes
                translated into HTML curly quote entities.

    Example input:  `Isn't this fun?'
    Example output: ‘Isn’t this fun?’
    """
    smart = smartchars(language)

    text = text.replace(r'`', smart.osquote)
    text = text.replace(r"'", smart.csquote)
    return text


def educateDashes(text):
    """
    Parameter:  String (unicode or bytes).
    Returns:    The `text`, with each instance of "--" translated to
                an em-dash character.
    """

    text = text.replace(r'---', smartchars.endash)  # en (yes, backwards)
    text = text.replace(r'--', smartchars.emdash)   # em (yes, backwards)
    return text


def educateDashesOldSchool(text):
    """
    Parameter:  String (unicode or bytes).
    Returns:    The `text`, with each instance of "--" translated to
                an en-dash character, and each "---" translated to
                an em-dash character.
    """

    text = text.replace(r'---', smartchars.emdash)
    text = text.replace(r'--', smartchars.endash)
    return text


def educateDashesOldSchoolInverted(text):
    """
    Parameter:  String (unicode or bytes).
    Returns:    The `text`, with each instance of "--" translated to
                an em-dash character, and each "---" translated to
                an en-dash character. Two reasons why: First, unlike the
                en- and em-dash syntax supported by
                EducateDashesOldSchool(), it's compatible with existing
                entries written before SmartyPants 1.1, back when "--" was
                only used for em-dashes.  Second, em-dashes are more
                common than en-dashes, and so it sort of makes sense that
                the shortcut should be shorter to type. (Thanks to Aaron
                Swartz for the idea.)
    """
    text = text.replace(r'---', smartchars.endash)    # em
    text = text.replace(r'--', smartchars.emdash)    # en
    return text


def educateEllipses(text):
    """
    Parameter:  String (unicode or bytes).
    Returns:    The `text`, with each instance of "..." translated to
                an ellipsis character.

    Example input:  Huh...?
    Example output: Huh…?
    """

    text = text.replace(r'...', smartchars.ellipsis)
    text = text.replace(r'. . .', smartchars.ellipsis)
    return text


def stupefyEntities(text, language='en'):
    """
    Parameter:  String (unicode or bytes).
    Returns:    The `text`, with each SmartyPants character translated to
                its ASCII counterpart.

    Example input:  “Hello — world.”
    Example output: "Hello -- world."
    """
    smart = smartchars(language)

    text = text.replace(smart.endash, "-")
    text = text.replace(smart.emdash, "--")
    text = text.replace(smart.osquote, "'")  # open secondary quote
    text = text.replace(smart.csquote, "'")  # close secondary quote
    text = text.replace(smart.opquote, '"')  # open primary quote
    text = text.replace(smart.cpquote, '"')  # close primary quote
    text = text.replace(smart.ellipsis, '...')

    return text


def processEscapes(text, restore=False):
    r"""
    Parameter:  String (unicode or bytes).
    Returns:    The `text`, with after processing the following backslash
                escape sequences. This is useful if you want to force a "dumb"
                quote or other character to appear.

                Escape  Value
                ------  -----
                \\      &#92;
                \"      &#34;
                \'      &#39;
                \.      &#46;
                \-      &#45;
                \`      &#96;
    """
    replacements = ((r'\\', r'&#92;'),
                    (r'\"', r'&#34;'),
                    (r"\'", r'&#39;'),
                    (r'\.', r'&#46;'),
                    (r'\-', r'&#45;'),
                    (r'\`', r'&#96;'))
    if restore:
        for (ch, rep) in replacements:
            text = text.replace(rep, ch[1])
    else:
        for (ch, rep) in replacements:
            text = text.replace(ch, rep)

    return text


def tokenize(text):
    """
    Parameter:  String containing HTML markup.
    Returns:    An iterator that yields the tokens comprising the input
                string. Each token is either a tag (possibly with nested,
                tags contained therein, such as <a href="<MTFoo>">, or a
                run of text between tags. Each yielded element is a
                two-element tuple; the first is either 'tag' or 'text';
                the second is the actual value.

    Based on the _tokenize() subroutine from Brad Choate's MTRegex plugin.
    """
    tag_soup = re.compile(r'([^<]*)(<[^>]*>)')
    token_match = tag_soup.search(text)
    previous_end = 0

    while token_match is not None:
        if token_match.group(1):
            yield 'text', token_match.group(1)
        yield 'tag', token_match.group(2)
        previous_end = token_match.end()
        token_match = tag_soup.search(text, token_match.end())

    if previous_end < len(text):
        yield 'text', text[previous_end:]


if __name__ == "__main__":

    import itertools
    import locale
    try:
        locale.setlocale(locale.LC_ALL, '')  # set to user defaults
        defaultlanguage = locale.getlocale()[0]
    except:  # NoQA: E722 (catchall)
        defaultlanguage = 'en'

    # Normalize and drop unsupported subtags:
    defaultlanguage = defaultlanguage.lower().replace('-', '_')
    # split (except singletons, which mark the following tag as non-standard):
    defaultlanguage = re.sub(r'_([a-zA-Z0-9])_', r'_\1-', defaultlanguage)
    _subtags = list(defaultlanguage.split('_'))
    _basetag = _subtags.pop(0)
    # find all combinations of subtags
    for n in range(len(_subtags), 0, -1):
        for tags in itertools.combinations(_subtags, n):
            _tag = '-'.join((_basetag, *tags))
            if _tag in smartchars.quotes:
                defaultlanguage = _tag
                break
        else:
            if _basetag in smartchars.quotes:
                defaultlanguage = _basetag
            else:
                defaultlanguage = 'en'

    import argparse
    parser = argparse.ArgumentParser(
                description='Filter <input> making ASCII punctuation "smart".')
    # TODO: require input arg or other means to print USAGE instead of waiting.
    # parser.add_argument("input", help="Input stream, use '-' for stdin.")
    parser.add_argument("-a", "--action", default="1",
                        help="what to do with the input (see --actionhelp)")
    parser.add_argument("-e", "--encoding", default="utf-8",
                        help="text encoding")
    parser.add_argument("-l", "--language", default=defaultlanguage,
                        help="text language (BCP47 tag), "
                             f"Default: {defaultlanguage}")
    parser.add_argument("-q", "--alternative-quotes", action="store_true",
                        help="use alternative quote style")
    parser.add_argument("--doc", action="store_true",
                        help="print documentation")
    parser.add_argument("--actionhelp", action="store_true",
                        help="list available actions")
    parser.add_argument("--stylehelp", action="store_true",
                        help="list available quote styles")
    parser.add_argument("--test", action="store_true",
                        help="perform short self-test")
    args = parser.parse_args()

    if args.doc:
        print(__doc__)
    elif args.actionhelp:
        print(options)
    elif args.stylehelp:
        print()
        print("Available styles (primary open/close, secondary open/close)")
        print("language tag   quotes")
        print("============   ======")
        for key in sorted(smartchars.quotes.keys()):
            print("%-14s %s" % (key, smartchars.quotes[key]))
    elif args.test:
        # Unit test output goes to stderr.
        import unittest

        class TestSmartypantsAllAttributes(unittest.TestCase):
            # the default attribute is "1", which means "all".
            def test_dates(self) -> None:
                self.assertEqual(smartyPants("1440-80's"), "1440-80’s")
                self.assertEqual(smartyPants("1440-'80s"), "1440-’80s")
                self.assertEqual(smartyPants("1440---'80s"), "1440–’80s")
                self.assertEqual(smartyPants("1960's"), "1960’s")
                self.assertEqual(smartyPants("one two '60s"), "one two ’60s")
                self.assertEqual(smartyPants("'60s"), "’60s")

            def test_educated_quotes(self) -> None:
                self.assertEqual(smartyPants('"Isn\'t this fun?"'),
                                 '“Isn’t this fun?”')

            def test_html_tags(self) -> None:
                text = '<a src="foo">more</a>'
                self.assertEqual(smartyPants(text), text)

        suite = unittest.TestLoader().loadTestsFromTestCase(
                                            TestSmartypantsAllAttributes)
        unittest.TextTestRunner().run(suite)

    else:
        if args.alternative_quotes:
            if '-x-altquot' in args.language:
                args.language = args.language.replace('-x-altquot', '')
            else:
                args.language += '-x-altquot'
        text = sys.stdin.read()
        print(smartyPants(text, attr=args.action, language=args.language))

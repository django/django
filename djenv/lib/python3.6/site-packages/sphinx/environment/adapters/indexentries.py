# -*- coding: utf-8 -*-
"""
    sphinx.environment.adapters.indexentries
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Index entries adapters for sphinx.environment.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import bisect
import re
import unicodedata
from itertools import groupby

from six import text_type, iteritems

from sphinx.locale import _, __
from sphinx.util import split_into, logging

if False:
    # For type annotation
    from typing import Any, Dict, Pattern, List, Tuple  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA

logger = logging.getLogger(__name__)


class IndexEntries(object):
    def __init__(self, env):
        # type: (BuildEnvironment) -> None
        self.env = env

    def create_index(self, builder, group_entries=True,
                     _fixre=re.compile(r'(.*) ([(][^()]*[)])')):
        # type: (Builder, bool, Pattern) -> List[Tuple[unicode, List[Tuple[unicode, Any]]]]  # NOQA
        """Create the real index from the collected index entries."""
        from sphinx.environment import NoUri

        new = {}  # type: Dict[unicode, List]

        def add_entry(word, subword, main, link=True, dic=new, key=None):
            # type: (unicode, unicode, unicode, bool, Dict, unicode) -> None
            # Force the word to be unicode if it's a ASCII bytestring.
            # This will solve problems with unicode normalization later.
            # For instance the RFC role will add bytestrings at the moment
            word = text_type(word)
            entry = dic.get(word)
            if not entry:
                dic[word] = entry = [[], {}, key]
            if subword:
                add_entry(subword, '', main, link=link, dic=entry[1], key=key)
            elif link:
                try:
                    uri = builder.get_relative_uri('genindex', fn) + '#' + tid
                except NoUri:
                    pass
                else:
                    # maintain links in sorted/deterministic order
                    bisect.insort(entry[0], (main, uri))

        for fn, entries in iteritems(self.env.indexentries):
            # new entry types must be listed in directives/other.py!
            for type, value, tid, main, index_key in entries:
                try:
                    if type == 'single':
                        try:
                            entry, subentry = split_into(2, 'single', value)
                        except ValueError:
                            entry, = split_into(1, 'single', value)
                            subentry = ''
                        add_entry(entry, subentry, main, key=index_key)
                    elif type == 'pair':
                        first, second = split_into(2, 'pair', value)
                        add_entry(first, second, main, key=index_key)
                        add_entry(second, first, main, key=index_key)
                    elif type == 'triple':
                        first, second, third = split_into(3, 'triple', value)
                        add_entry(first, second + ' ' + third, main, key=index_key)
                        add_entry(second, third + ', ' + first, main, key=index_key)
                        add_entry(third, first + ' ' + second, main, key=index_key)
                    elif type == 'see':
                        first, second = split_into(2, 'see', value)
                        add_entry(first, _('see %s') % second, None,
                                  link=False, key=index_key)
                    elif type == 'seealso':
                        first, second = split_into(2, 'see', value)
                        add_entry(first, _('see also %s') % second, None,
                                  link=False, key=index_key)
                    else:
                        logger.warning(__('unknown index entry type %r'), type, location=fn)
                except ValueError as err:
                    logger.warning(str(err), location=fn)

        # sort the index entries; put all symbols at the front, even those
        # following the letters in ASCII, this is where the chr(127) comes from
        def keyfunc(entry):
            # type: (Tuple[unicode, List]) -> Tuple[unicode, unicode]
            key, (void, void, category_key) = entry
            if category_key:
                # using specified category key to sort
                key = category_key
            lckey = unicodedata.normalize('NFD', key.lower())
            if lckey.startswith(u'\N{RIGHT-TO-LEFT MARK}'):
                lckey = lckey[1:]
            if lckey[0:1].isalpha() or lckey.startswith('_'):
                lckey = chr(127) + lckey
            # ensure a determinstic order *within* letters by also sorting on
            # the entry itself
            return (lckey, entry[0])
        newlist = sorted(new.items(), key=keyfunc)

        if group_entries:
            # fixup entries: transform
            #   func() (in module foo)
            #   func() (in module bar)
            # into
            #   func()
            #     (in module foo)
            #     (in module bar)
            oldkey = ''  # type: unicode
            oldsubitems = None  # type: Dict[unicode, List]
            i = 0
            while i < len(newlist):
                key, (targets, subitems, _key) = newlist[i]
                # cannot move if it has subitems; structure gets too complex
                if not subitems:
                    m = _fixre.match(key)
                    if m:
                        if oldkey == m.group(1):
                            # prefixes match: add entry as subitem of the
                            # previous entry
                            oldsubitems.setdefault(m.group(2), [[], {}, _key])[0].\
                                extend(targets)
                            del newlist[i]
                            continue
                        oldkey = m.group(1)
                    else:
                        oldkey = key
                oldsubitems = subitems
                i += 1

        # group the entries by letter
        def keyfunc2(item):
            # type: (Tuple[unicode, List]) -> unicode
            # hack: mutating the subitems dicts to a list in the keyfunc
            k, v = item
            v[1] = sorted((si, se) for (si, (se, void, void)) in iteritems(v[1]))
            if v[2] is None:
                # now calculate the key
                if k.startswith(u'\N{RIGHT-TO-LEFT MARK}'):
                    k = k[1:]
                letter = unicodedata.normalize('NFD', k[0])[0].upper()
                if letter.isalpha() or letter == '_':
                    return letter
                else:
                    # get all other symbols under one heading
                    return _('Symbols')
            else:
                return v[2]
        return [(key_, list(group))
                for (key_, group) in groupby(newlist, keyfunc2)]

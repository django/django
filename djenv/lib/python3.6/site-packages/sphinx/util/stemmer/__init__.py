# -*- coding: utf-8 -*-
"""
    sphinx.util.stemmer
    ~~~~~~~~~~~~~~~~~~~

    Word stemming utilities for Sphinx.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from sphinx.util.stemmer.porter import PorterStemmer

try:
    from Stemmer import Stemmer as _PyStemmer
    PYSTEMMER = True
except ImportError:
    PYSTEMMER = False


class BaseStemmer(object):
    def stem(self, word):
        # type: (unicode) -> unicode
        raise NotImplementedError()


class PyStemmer(BaseStemmer):
    def __init__(self):
        # type: () -> None
        self.stemmer = _PyStemmer('porter')

    def stem(self, word):
        # type: (unicode) -> unicode
        return self.stemmer.stemWord(word)


class StandardStemmer(BaseStemmer, PorterStemmer):  # type: ignore
    """All those porter stemmer implementations look hideous;
    make at least the stem method nicer.
    """
    def stem(self, word):  # type: ignore
        # type: (unicode) -> unicode
        return PorterStemmer.stem(self, word, 0, len(word) - 1)


def get_stemmer():
    # type: () -> BaseStemmer
    if PYSTEMMER:
        return PyStemmer()
    else:
        return StandardStemmer()

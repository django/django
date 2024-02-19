"""Turkish search language: includes the JS Turkish stemmer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Set

import snowballstemmer

from sphinx.search import SearchLanguage


class SearchTurkish(SearchLanguage):
    lang = 'tr'
    language_name = 'Turkish'
    js_stemmer_rawcode = 'turkish-stemmer.js'
    stopwords: set[str] = set()

    def init(self, options: dict) -> None:
        self.stemmer = snowballstemmer.stemmer('turkish')

    def stem(self, word: str) -> str:
        return self.stemmer.stemWord(word.lower())

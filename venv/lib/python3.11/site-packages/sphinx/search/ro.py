"""Romanian search language: includes the JS Romanian stemmer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Set

import snowballstemmer

from sphinx.search import SearchLanguage


class SearchRomanian(SearchLanguage):
    lang = 'ro'
    language_name = 'Romanian'
    js_stemmer_rawcode = 'romanian-stemmer.js'
    stopwords: set[str] = set()

    def init(self, options: dict) -> None:
        self.stemmer = snowballstemmer.stemmer('romanian')

    def stem(self, word: str) -> str:
        return self.stemmer.stemWord(word.lower())

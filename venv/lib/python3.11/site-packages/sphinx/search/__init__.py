"""Create a full-text search index for offline search."""
from __future__ import annotations

import dataclasses
import functools
import html
import json
import pickle
import re
from importlib import import_module
from os import path
from typing import IO, TYPE_CHECKING, Any

from docutils import nodes
from docutils.nodes import Element, Node

from sphinx import addnodes, package_dir
from sphinx.environment import BuildEnvironment
from sphinx.util.index_entries import split_index_msg

if TYPE_CHECKING:
    from collections.abc import Iterable


class SearchLanguage:
    """
    This class is the base class for search natural language preprocessors.  If
    you want to add support for a new language, you should override the methods
    of this class.

    You should override `lang` class property too (e.g. 'en', 'fr' and so on).

    .. attribute:: stopwords

       This is a set of stop words of the target language.  Default `stopwords`
       is empty.  This word is used for building index and embedded in JS.

    .. attribute:: js_splitter_code

       Return splitter function of JavaScript version.  The function should be
       named as ``splitQuery``.  And it should take a string and return list of
       strings.

       .. versionadded:: 3.0

    .. attribute:: js_stemmer_code

       Return stemmer class of JavaScript version.  This class' name should be
       ``Stemmer`` and this class must have ``stemWord`` method.  This string is
       embedded as-is in searchtools.js.

       This class is used to preprocess search word which Sphinx HTML readers
       type, before searching index. Default implementation does nothing.
    """
    lang: str | None = None
    language_name: str | None = None
    stopwords: set[str] = set()
    js_splitter_code: str = ""
    js_stemmer_rawcode: str | None = None
    js_stemmer_code = """
/**
 * Dummy stemmer for languages without stemming rules.
 */
var Stemmer = function() {
  this.stemWord = function(w) {
    return w;
  }
}
"""

    _word_re = re.compile(r'\w+')

    def __init__(self, options: dict) -> None:
        self.options = options
        self.init(options)

    def init(self, options: dict) -> None:
        """
        Initialize the class with the options the user has given.
        """

    def split(self, input: str) -> list[str]:
        """
        This method splits a sentence into words.  Default splitter splits input
        at white spaces, which should be enough for most languages except CJK
        languages.
        """
        return self._word_re.findall(input)

    def stem(self, word: str) -> str:
        """
        This method implements stemming algorithm of the Python version.

        Default implementation does nothing.  You should implement this if the
        language has any stemming rules.

        This class is used to preprocess search words before registering them in
        the search index.  The stemming of the Python version and the JS version
        (given in the js_stemmer_code attribute) must be compatible.
        """
        return word

    def word_filter(self, word: str) -> bool:
        """
        Return true if the target word should be registered in the search index.
        This method is called after stemming.
        """
        return (
            len(word) == 0 or not (
                ((len(word) < 3) and (12353 < ord(word[0]) < 12436)) or
                (ord(word[0]) < 256 and (
                    word in self.stopwords
                ))))


# SearchEnglish imported after SearchLanguage is defined due to circular import
from sphinx.search.en import SearchEnglish


def parse_stop_word(source: str) -> set[str]:
    """
    Parse snowball style word list like this:

    * http://snowball.tartarus.org/algorithms/finnish/stop.txt
    """
    result: set[str] = set()
    for line in source.splitlines():
        line = line.split('|')[0]  # remove comment
        result.update(line.split())
    return result


# maps language name to module.class or directly a class
languages: dict[str, str | type[SearchLanguage]] = {
    'da': 'sphinx.search.da.SearchDanish',
    'de': 'sphinx.search.de.SearchGerman',
    'en': SearchEnglish,
    'es': 'sphinx.search.es.SearchSpanish',
    'fi': 'sphinx.search.fi.SearchFinnish',
    'fr': 'sphinx.search.fr.SearchFrench',
    'hu': 'sphinx.search.hu.SearchHungarian',
    'it': 'sphinx.search.it.SearchItalian',
    'ja': 'sphinx.search.ja.SearchJapanese',
    'nl': 'sphinx.search.nl.SearchDutch',
    'no': 'sphinx.search.no.SearchNorwegian',
    'pt': 'sphinx.search.pt.SearchPortuguese',
    'ro': 'sphinx.search.ro.SearchRomanian',
    'ru': 'sphinx.search.ru.SearchRussian',
    'sv': 'sphinx.search.sv.SearchSwedish',
    'tr': 'sphinx.search.tr.SearchTurkish',
    'zh': 'sphinx.search.zh.SearchChinese',
}


class _JavaScriptIndex:
    """
    The search index as JavaScript file that calls a function
    on the documentation search object to register the index.
    """

    PREFIX = 'Search.setIndex('
    SUFFIX = ')'

    def dumps(self, data: Any) -> str:
        return self.PREFIX + json.dumps(data) + self.SUFFIX

    def loads(self, s: str) -> Any:
        data = s[len(self.PREFIX):-len(self.SUFFIX)]
        if not data or not s.startswith(self.PREFIX) or not \
           s.endswith(self.SUFFIX):
            raise ValueError('invalid data')
        return json.loads(data)

    def dump(self, data: Any, f: IO) -> None:
        f.write(self.dumps(data))

    def load(self, f: IO) -> Any:
        return self.loads(f.read())


js_index = _JavaScriptIndex()


def _is_meta_keywords(
    node: nodes.meta,  # type: ignore[name-defined]
    lang: str | None,
) -> bool:
    if node.get('name') == 'keywords':
        meta_lang = node.get('lang')
        if meta_lang is None:  # lang not specified
            return True
        elif meta_lang == lang:  # matched to html_search_language
            return True

    return False


@dataclasses.dataclass
class WordStore:
    words: list[str] = dataclasses.field(default_factory=list)
    titles: list[tuple[str, str]] = dataclasses.field(default_factory=list)
    title_words: list[str] = dataclasses.field(default_factory=list)


class WordCollector(nodes.NodeVisitor):
    """
    A special visitor that collects words for the `IndexBuilder`.
    """

    def __init__(self, document: nodes.document, lang: SearchLanguage) -> None:
        super().__init__(document)
        self.found_words: list[str] = []
        self.found_titles: list[tuple[str, str]] = []
        self.found_title_words: list[str] = []
        self.lang = lang

    def dispatch_visit(self, node: Node) -> None:
        if isinstance(node, nodes.comment):
            raise nodes.SkipNode
        elif isinstance(node, nodes.raw):
            if 'html' in node.get('format', '').split():
                # Some people might put content in raw HTML that should be searched,
                # so we just amateurishly strip HTML tags and index the remaining
                # content
                nodetext = re.sub(r'<style.*?</style>', '', node.astext(), flags=re.IGNORECASE|re.DOTALL)
                nodetext = re.sub(r'<script.*?</script>', '', nodetext, flags=re.IGNORECASE|re.DOTALL)
                nodetext = re.sub(r'<[^<]+?>', '', nodetext)
                self.found_words.extend(self.lang.split(nodetext))
            raise nodes.SkipNode
        elif isinstance(node, nodes.Text):
            self.found_words.extend(self.lang.split(node.astext()))
        elif isinstance(node, nodes.title):
            title = node.astext()
            ids = node.parent['ids']
            self.found_titles.append((title, ids[0] if ids else None))
            self.found_title_words.extend(self.lang.split(title))
        elif isinstance(node, Element) and _is_meta_keywords(node, self.lang.lang):
            keywords = node['content']
            keywords = [keyword.strip() for keyword in keywords.split(',')]
            self.found_words.extend(keywords)


class IndexBuilder:
    """
    Helper class that creates a search index based on the doctrees
    passed to the `feed` method.
    """
    formats = {
        'json':     json,
        'pickle':   pickle
    }

    def __init__(self, env: BuildEnvironment, lang: str, options: dict, scoring: str) -> None:
        self.env = env
        # docname -> title
        self._titles: dict[str, str] = env._search_index_titles
        # docname -> filename
        self._filenames: dict[str, str] = env._search_index_filenames
        # stemmed words -> set(docname)
        self._mapping: dict[str, set[str]] = env._search_index_mapping
        # stemmed words in titles -> set(docname)
        self._title_mapping: dict[str, set[str]] = env._search_index_title_mapping
        # docname -> all titles in document
        self._all_titles: dict[str, list[tuple[str, str]]] = env._search_index_all_titles
        # docname -> list(index entry)
        self._index_entries: dict[str, list[tuple[str, str, str]]] = env._search_index_index_entries
        # objtype -> index
        self._objtypes: dict[tuple[str, str], int] = env._search_index_objtypes
        # objtype index -> (domain, type, objname (localized))
        self._objnames: dict[int, tuple[str, str, str]] = env._search_index_objnames
        # add language-specific SearchLanguage instance
        lang_class = languages.get(lang)

        # fallback; try again with language-code
        if lang_class is None and '_' in lang:
            lang_class = languages.get(lang.split('_')[0])

        if lang_class is None:
            self.lang: SearchLanguage = SearchEnglish(options)
        elif isinstance(lang_class, str):
            module, classname = lang_class.rsplit('.', 1)
            lang_class: type[SearchLanguage] = getattr(import_module(module), classname)  # type: ignore[no-redef]
            self.lang = lang_class(options)  # type: ignore[operator]
        else:
            # it's directly a class (e.g. added by app.add_search_language)
            self.lang = lang_class(options)

        if scoring:
            with open(scoring, 'rb') as fp:
                self.js_scorer_code = fp.read().decode()
        else:
            self.js_scorer_code = ''
        self.js_splitter_code = ""

    def load(self, stream: IO, format: Any) -> None:
        """Reconstruct from frozen data."""
        if isinstance(format, str):
            format = self.formats[format]
        frozen = format.load(stream)
        # if an old index is present, we treat it as not existing.
        if not isinstance(frozen, dict) or \
           frozen.get('envversion') != self.env.version:
            raise ValueError('old format')
        index2fn = frozen['docnames']
        self._filenames = dict(zip(index2fn, frozen['filenames']))
        self._titles = dict(zip(index2fn, frozen['titles']))
        self._all_titles = {}

        for docname in self._titles.keys():
            self._all_titles[docname] = []
        for title, doc_tuples in frozen['alltitles'].items():
            for doc, titleid in doc_tuples:
                self._all_titles[index2fn[doc]].append((title, titleid))

        def load_terms(mapping: dict[str, Any]) -> dict[str, set[str]]:
            rv = {}
            for k, v in mapping.items():
                if isinstance(v, int):
                    rv[k] = {index2fn[v]}
                else:
                    rv[k] = {index2fn[i] for i in v}
            return rv

        self._mapping = load_terms(frozen['terms'])
        self._title_mapping = load_terms(frozen['titleterms'])
        # no need to load keywords/objtypes

    def dump(self, stream: IO, format: Any) -> None:
        """Dump the frozen index to a stream."""
        if isinstance(format, str):
            format = self.formats[format]
        format.dump(self.freeze(), stream)

    def get_objects(self, fn2index: dict[str, int]
                    ) -> dict[str, list[tuple[int, int, int, str, str]]]:
        rv: dict[str, list[tuple[int, int, int, str, str]]] = {}
        otypes = self._objtypes
        onames = self._objnames
        for domainname, domain in sorted(self.env.domains.items()):
            for fullname, dispname, type, docname, anchor, prio in \
                    sorted(domain.get_objects()):
                if docname not in fn2index:
                    continue
                if prio < 0:
                    continue
                fullname = html.escape(fullname)
                dispname = html.escape(dispname)
                prefix, _, name = dispname.rpartition('.')
                plist = rv.setdefault(prefix, [])
                try:
                    typeindex = otypes[domainname, type]
                except KeyError:
                    typeindex = len(otypes)
                    otypes[domainname, type] = typeindex
                    otype = domain.object_types.get(type)
                    if otype:
                        # use str() to fire translation proxies
                        onames[typeindex] = (domainname, type,
                                             str(domain.get_type_name(otype)))
                    else:
                        onames[typeindex] = (domainname, type, type)
                if anchor == fullname:
                    shortanchor = ''
                elif anchor == type + '-' + fullname:
                    shortanchor = '-'
                else:
                    shortanchor = anchor
                plist.append((fn2index[docname], typeindex, prio, shortanchor, name))
        return rv

    def get_terms(self, fn2index: dict) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        rvs: tuple[dict[str, list[str]], dict[str, list[str]]] = ({}, {})
        for rv, mapping in zip(rvs, (self._mapping, self._title_mapping)):
            for k, v in mapping.items():
                if len(v) == 1:
                    fn, = v
                    if fn in fn2index:
                        rv[k] = fn2index[fn]
                else:
                    rv[k] = sorted([fn2index[fn] for fn in v if fn in fn2index])
        return rvs

    def freeze(self) -> dict[str, Any]:
        """Create a usable data structure for serializing."""
        docnames, titles = zip(*sorted(self._titles.items()))
        filenames = [self._filenames.get(docname) for docname in docnames]
        fn2index = {f: i for (i, f) in enumerate(docnames)}
        terms, title_terms = self.get_terms(fn2index)

        objects = self.get_objects(fn2index)  # populates _objtypes
        objtypes = {v: k[0] + ':' + k[1] for (k, v) in self._objtypes.items()}
        objnames = self._objnames

        alltitles: dict[str, list[tuple[int, str]]] = {}
        for docname, titlelist in self._all_titles.items():
            for title, titleid in titlelist:
                alltitles.setdefault(title, []).append((fn2index[docname], titleid))

        index_entries: dict[str, list[tuple[int, str]]] = {}
        for docname, entries in self._index_entries.items():
            for entry, entry_id, main_entry in entries:
                index_entries.setdefault(entry.lower(), []).append((fn2index[docname], entry_id))

        return dict(docnames=docnames, filenames=filenames, titles=titles, terms=terms,
                    objects=objects, objtypes=objtypes, objnames=objnames,
                    titleterms=title_terms, envversion=self.env.version,
                    alltitles=alltitles, indexentries=index_entries)

    def label(self) -> str:
        return f"{self.lang.language_name} (code: {self.lang.lang})"

    def prune(self, docnames: Iterable[str]) -> None:
        """Remove data for all docnames not in the list."""
        new_titles = {}
        new_alltitles = {}
        new_filenames = {}
        for docname in docnames:
            if docname in self._titles:
                new_titles[docname] = self._titles[docname]
                new_alltitles[docname] = self._all_titles[docname]
                new_filenames[docname] = self._filenames[docname]
        self._titles = new_titles
        self._filenames = new_filenames
        self._all_titles = new_alltitles
        for wordnames in self._mapping.values():
            wordnames.intersection_update(docnames)
        for wordnames in self._title_mapping.values():
            wordnames.intersection_update(docnames)

    def feed(self, docname: str, filename: str, title: str, doctree: nodes.document) -> None:
        """Feed a doctree to the index."""
        self._titles[docname] = title
        self._filenames[docname] = filename

        word_store = self._word_collector(doctree)

        _filter = self.lang.word_filter
        _stem = self.lang.stem

        # memoise self.lang.stem
        @functools.lru_cache(maxsize=None)
        def stem(word_to_stem: str) -> str:
            return _stem(word_to_stem).lower()

        self._all_titles[docname] = word_store.titles

        for word in word_store.title_words:
            # add stemmed and unstemmed as the stemmer must not remove words
            # from search index.
            stemmed_word = stem(word)
            if _filter(stemmed_word):
                self._title_mapping.setdefault(stemmed_word, set()).add(docname)
            elif _filter(word):
                self._title_mapping.setdefault(word, set()).add(docname)

        for word in word_store.words:
            # add stemmed and unstemmed as the stemmer must not remove words
            # from search index.
            stemmed_word = stem(word)
            if not _filter(stemmed_word) and _filter(word):
                stemmed_word = word
            already_indexed = docname in self._title_mapping.get(stemmed_word, ())
            if _filter(stemmed_word) and not already_indexed:
                self._mapping.setdefault(stemmed_word, set()).add(docname)

        # find explicit entries within index directives
        _index_entries: set[tuple[str, str, str]] = set()
        for node in doctree.findall(addnodes.index):
            for entry_type, value, target_id, main, _category_key in node['entries']:
                try:
                    result = split_index_msg(entry_type, value)
                except ValueError:
                    pass
                else:
                    target_id = target_id or ''
                    if entry_type in {'see', 'seealso'}:
                        _index_entries.add((result[0], target_id, main))
                    _index_entries |= {(x, target_id, main) for x in result}

        self._index_entries[docname] = sorted(_index_entries)

    def _word_collector(self, doctree: nodes.document) -> WordStore:
        def _visit_nodes(node):
            if isinstance(node, nodes.comment):
                return
            elif isinstance(node, nodes.raw):
                if 'html' in node.get('format', '').split():
                    # Some people might put content in raw HTML that should be searched,
                    # so we just amateurishly strip HTML tags and index the remaining
                    # content
                    nodetext = re.sub(r'<style.*?</style>', '', node.astext(),
                                      flags=re.IGNORECASE | re.DOTALL)
                    nodetext = re.sub(r'<script.*?</script>', '', nodetext,
                                      flags=re.IGNORECASE | re.DOTALL)
                    nodetext = re.sub(r'<[^<]+?>', '', nodetext)
                    word_store.words.extend(split(nodetext))
                return
            elif (isinstance(node, nodes.meta)  # type: ignore[attr-defined]
                  and _is_meta_keywords(node, language)):
                keywords = [keyword.strip() for keyword in node['content'].split(',')]
                word_store.words.extend(keywords)
            elif isinstance(node, nodes.Text):
                word_store.words.extend(split(node.astext()))
            elif isinstance(node, nodes.title):
                title = node.astext()
                ids = node.parent['ids']
                word_store.titles.append((title, ids[0] if ids else None))
                word_store.title_words.extend(split(title))
            for child in node.children:
                _visit_nodes(child)
            return

        word_store = WordStore()
        split = self.lang.split
        language = self.lang.lang
        _visit_nodes(doctree)
        return word_store

    def context_for_searchtool(self) -> dict[str, Any]:
        if self.lang.js_splitter_code:
            js_splitter_code = self.lang.js_splitter_code
        else:
            js_splitter_code = self.js_splitter_code

        return {
            'search_language_stemming_code': self.get_js_stemmer_code(),
            'search_language_stop_words': json.dumps(sorted(self.lang.stopwords)),
            'search_scorer_tool': self.js_scorer_code,
            'search_word_splitter_code': js_splitter_code,
        }

    def get_js_stemmer_rawcodes(self) -> list[str]:
        """Returns a list of non-minified stemmer JS files to copy."""
        if self.lang.js_stemmer_rawcode:
            return [
                path.join(package_dir, 'search', 'non-minified-js', fname)
                for fname in ('base-stemmer.js', self.lang.js_stemmer_rawcode)
            ]
        else:
            return []

    def get_js_stemmer_rawcode(self) -> str | None:
        return None

    def get_js_stemmer_code(self) -> str:
        """Returns JS code that will be inserted into language_data.js."""
        if self.lang.js_stemmer_rawcode:
            js_dir = path.join(package_dir, 'search', 'minified-js')
            with open(path.join(js_dir, 'base-stemmer.js'), encoding='utf-8') as js_file:
                base_js = js_file.read()
            with open(path.join(js_dir, self.lang.js_stemmer_rawcode), encoding='utf-8') as js_file:
                language_js = js_file.read()
            return ('%s\n%s\nStemmer = %sStemmer;' %
                    (base_js, language_js, self.lang.language_name))
        else:
            return self.lang.js_stemmer_code

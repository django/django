__all__ = ('language', 'stemmer')

from .danish_stemmer import DanishStemmer
from .dutch_stemmer import DutchStemmer
from .english_stemmer import EnglishStemmer
from .finnish_stemmer import FinnishStemmer
from .french_stemmer import FrenchStemmer
from .german_stemmer import GermanStemmer
from .hungarian_stemmer import HungarianStemmer
from .italian_stemmer import ItalianStemmer
from .norwegian_stemmer import NorwegianStemmer
from .porter_stemmer import PorterStemmer
from .portuguese_stemmer import PortugueseStemmer
from .romanian_stemmer import RomanianStemmer
from .russian_stemmer import RussianStemmer
from .spanish_stemmer import SpanishStemmer
from .swedish_stemmer import SwedishStemmer
from .turkish_stemmer import TurkishStemmer

_languages = {
    'danish': DanishStemmer,
    'dutch': DutchStemmer,
    'english': EnglishStemmer,
    'finnish': FinnishStemmer,
    'french': FrenchStemmer,
    'german': GermanStemmer,
    'hungarian': HungarianStemmer,
    'italian': ItalianStemmer,
    'norwegian': NorwegianStemmer,
    'porter': PorterStemmer,
    'portuguese': PortugueseStemmer,
    'romanian': RomanianStemmer,
    'russian': RussianStemmer,
    'spanish': SpanishStemmer,
    'swedish': SwedishStemmer,
    'turkish': TurkishStemmer,
}

try:
    import Stemmer
    cext_available = True
except ImportError:
    cext_available = False

def algorithms():
    if cext_available:
        return Stemmer.language()
    else:
        return list(_languages.keys())

def stemmer(lang):
    if cext_available:
        return Stemmer.Stemmer(lang)
    if lang.lower() in _languages:
        return _languages[lang.lower()]()
    else:
        raise KeyError("Stemming algorithm '%s' not found" % lang)

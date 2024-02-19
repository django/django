__all__ = ('language', 'stemmer')

from .arabic_stemmer import ArabicStemmer
from .armenian_stemmer import ArmenianStemmer
from .basque_stemmer import BasqueStemmer
from .catalan_stemmer import CatalanStemmer
from .danish_stemmer import DanishStemmer
from .dutch_stemmer import DutchStemmer
from .english_stemmer import EnglishStemmer
from .finnish_stemmer import FinnishStemmer
from .french_stemmer import FrenchStemmer
from .german_stemmer import GermanStemmer
from .greek_stemmer import GreekStemmer
from .hindi_stemmer import HindiStemmer
from .hungarian_stemmer import HungarianStemmer
from .indonesian_stemmer import IndonesianStemmer
from .irish_stemmer import IrishStemmer
from .italian_stemmer import ItalianStemmer
from .lithuanian_stemmer import LithuanianStemmer
from .nepali_stemmer import NepaliStemmer
from .norwegian_stemmer import NorwegianStemmer
from .porter_stemmer import PorterStemmer
from .portuguese_stemmer import PortugueseStemmer
from .romanian_stemmer import RomanianStemmer
from .russian_stemmer import RussianStemmer
from .serbian_stemmer import SerbianStemmer
from .spanish_stemmer import SpanishStemmer
from .swedish_stemmer import SwedishStemmer
from .tamil_stemmer import TamilStemmer
from .turkish_stemmer import TurkishStemmer
from .yiddish_stemmer import YiddishStemmer

_languages = {
    'arabic': ArabicStemmer,
    'armenian': ArmenianStemmer,
    'basque': BasqueStemmer,
    'catalan': CatalanStemmer,
    'danish': DanishStemmer,
    'dutch': DutchStemmer,
    'english': EnglishStemmer,
    'finnish': FinnishStemmer,
    'french': FrenchStemmer,
    'german': GermanStemmer,
    'greek': GreekStemmer,
    'hindi': HindiStemmer,
    'hungarian': HungarianStemmer,
    'indonesian': IndonesianStemmer,
    'irish': IrishStemmer,
    'italian': ItalianStemmer,
    'lithuanian': LithuanianStemmer,
    'nepali': NepaliStemmer,
    'norwegian': NorwegianStemmer,
    'porter': PorterStemmer,
    'portuguese': PortugueseStemmer,
    'romanian': RomanianStemmer,
    'russian': RussianStemmer,
    'serbian': SerbianStemmer,
    'spanish': SpanishStemmer,
    'swedish': SwedishStemmer,
    'tamil': TamilStemmer,
    'turkish': TurkishStemmer,
    'yiddish': YiddishStemmer,
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

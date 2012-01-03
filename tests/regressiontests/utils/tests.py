"""
Tests for django.utils.
"""
from __future__ import absolute_import

from .dateformat import DateFormatTests
from .feedgenerator import FeedgeneratorTest
from .module_loading import DefaultLoader, EggLoader, CustomLoader
from .termcolors import TermColorTests
from .html import TestUtilsHtml
from .http import TestUtilsHttp
from .checksums import TestUtilsChecksums
from .text import TestUtilsText
from .simplelazyobject import TestUtilsSimpleLazyObject
from .decorators import DecoratorFromMiddlewareTests
from .functional import FunctionalTestCase
from .timesince import TimesinceTests
from .datastructures import (MultiValueDictTests, SortedDictTests,
    DictWrapperTests, ImmutableListTests, DotExpandedDictTests, MergeDictTests)
from .tzinfo import TzinfoTests
from .datetime_safe import DatetimeTests
from .baseconv import TestBaseConv
from .jslex import JsTokensTest, JsToCForGettextTest
from .ipv6 import TestUtilsIPv6
from .timezone import TimezoneTests
from .crypto import TestUtilsCryptoPBKDF2
from .archive import TestZip, TestTar, TestGzipTar, TestBzip2Tar
from .regex_helper import NormalizeTests

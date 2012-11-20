"""
Tests for django.utils.
"""
from __future__ import absolute_import

from .archive import TestBzip2Tar, TestGzipTar, TestTar, TestZip
from .baseconv import TestBaseConv
from .checksums import TestUtilsChecksums
from .crypto import TestUtilsCryptoMisc, TestUtilsCryptoPBKDF2
from .datastructures import (DictWrapperTests, ImmutableListTests,
    MergeDictTests, MultiValueDictTests, SortedDictTests)
from .dateformat import DateFormatTests
from .dateparse import DateParseTests
from .datetime_safe import DatetimeTests
from .decorators import DecoratorFromMiddlewareTests
from .encoding import TestEncodingUtils
from .feedgenerator import FeedgeneratorTest
from .functional import FunctionalTestCase
from .html import TestUtilsHtml
from .http import TestUtilsHttp, ETagProcessingTests, HttpDateProcessingTests
from .ipv6 import TestUtilsIPv6
from .jslex import JsToCForGettextTest, JsTokensTest
from .module_loading import CustomLoader, DefaultLoader, EggLoader
from .numberformat import TestNumberFormat
from .os_utils import SafeJoinTests
from .regex_helper import NormalizeTests
from .simplelazyobject import TestUtilsSimpleLazyObject
from .termcolors import TermColorTests
from .text import TestUtilsText
from .timesince import TimesinceTests
from .timezone import TimezoneTests
from .tzinfo import TzinfoTests

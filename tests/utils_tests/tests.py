"""
Tests for django.utils.
"""
from __future__ import absolute_import

from .test_archive import TestBzip2Tar, TestGzipTar, TestTar, TestZip
from .test_baseconv import TestBaseConv
from .test_checksums import TestUtilsChecksums
from .test_crypto import TestUtilsCryptoMisc, TestUtilsCryptoPBKDF2
from .test_datastructures import (DictWrapperTests, ImmutableListTests,
    MergeDictTests, MultiValueDictTests, SortedDictTests)
from .test_dateformat import DateFormatTests
from .test_dateparse import DateParseTests
from .test_datetime_safe import DatetimeTests
from .test_decorators import DecoratorFromMiddlewareTests
from .test_encoding import TestEncodingUtils
from .test_feedgenerator import FeedgeneratorTest
from .test_functional import FunctionalTestCase
from .test_html import TestUtilsHtml
from .test_http import TestUtilsHttp, ETagProcessingTests, HttpDateProcessingTests
from .test_itercompat import TestIsIterator
from .test_ipv6 import TestUtilsIPv6
from .test_jslex import JsToCForGettextTest, JsTokensTest
from .test_module_loading import (CustomLoader, DefaultLoader, EggLoader,
    ModuleImportTestCase)
from .test_numberformat import TestNumberFormat
from .test_os_utils import SafeJoinTests
from .test_regex_helper import NormalizeTests
from .test_simplelazyobject import TestUtilsSimpleLazyObject
from .test_termcolors import TermColorTests
from .test_text import TestUtilsText
from .test_timesince import TimesinceTests
from .test_timezone import TimezoneTests
from .test_tzinfo import TzinfoTests

from __future__ import absolute_import

from .debug import (DebugViewTests, ExceptionReporterTests,
    ExceptionReporterTests, PlainTextReportTests, ExceptionReporterFilterTests,
    AjaxResponseExceptionReporterFilter)
from .defaults import DefaultsTests
from .generic.create_update import (UpdateDeleteObjectTest, CreateObjectTest,
    PostSaveRedirectTests, NoPostSaveNoAbsoluteUrl, AbsoluteUrlNoPostSave)
from .generic.date_based import MonthArchiveTest, ObjectDetailTest, DayArchiveTests
from .generic.object_list import ObjectListTest
from .generic.simple import RedirectToTest
from .i18n import JsI18NTests, I18NTests, JsI18NTestsMultiPackage
from .shortcuts import ShortcutTests
from .specials import URLHandling
from .static import StaticHelperTest, StaticTests

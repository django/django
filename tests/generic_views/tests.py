from __future__ import absolute_import

from .test_base import (ViewTest, TemplateViewTest, RedirectViewTest,
    GetContextDataTest)
from .test_dates import (ArchiveIndexViewTests, YearArchiveViewTests,
    MonthArchiveViewTests, WeekArchiveViewTests, DayArchiveViewTests,
    DateDetailViewTests)
from .test_detail import DetailViewTest
from .test_edit import (FormMixinTests, BasicFormTests, ModelFormMixinTests,
    CreateViewTests, UpdateViewTests, DeleteViewTests)
from .test_list import ListViewTests

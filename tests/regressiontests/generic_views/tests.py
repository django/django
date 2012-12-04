from __future__ import absolute_import

from .base import (ViewTest, TemplateViewTest, RedirectViewTest,
    GetContextDataTest)
from .dates import (ArchiveIndexViewTests, YearArchiveViewTests,
    MonthArchiveViewTests, WeekArchiveViewTests, DayArchiveViewTests,
    DateDetailViewTests)
from .detail import DetailViewTest
from .edit import (FormMixinTests, BasicFormTests, ModelFormMixinTests,
    CreateViewTests, UpdateViewTests, DeleteViewTests)
from .list import ListViewTests

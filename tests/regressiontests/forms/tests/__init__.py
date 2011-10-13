from __future__ import absolute_import

from .error_messages import (FormsErrorMessagesTestCase,
    ModelChoiceFieldErrorMessagesTestCase)
from .extra import FormsExtraTestCase, FormsExtraL10NTestCase
from .fields import FieldsTests
from .forms import FormsTestCase
from .formsets import (FormsFormsetTestCase, FormsetAsFooTests,
    TestIsBoundBehavior, TestEmptyFormSet)
from .input_formats import (LocalizedTimeTests, CustomTimeInputFormatsTests,
    SimpleTimeFormatTests, LocalizedDateTests, CustomDateInputFormatsTests,
    SimpleDateFormatTests, LocalizedDateTimeTests,
    CustomDateTimeInputFormatsTests, SimpleDateTimeFormatTests)
from .media import FormsMediaTestCase, StaticFormsMediaTestCase
from .models import (TestTicket12510, ModelFormCallableModelDefault,
    FormsModelTestCase, RelatedModelFormTests)
from .regressions import FormsRegressionsTestCase
from .util import FormsUtilTestCase
from .validators import TestFieldWithValidators
from .widgets import (FormsWidgetTestCase, FormsI18NWidgetsTestCase,
    WidgetTests, ClearableFileInputTests)

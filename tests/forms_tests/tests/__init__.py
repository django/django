from __future__ import absolute_import

from .test_error_messages import (FormsErrorMessagesTestCase,
    ModelChoiceFieldErrorMessagesTestCase)
from .test_extra import FormsExtraTestCase, FormsExtraL10NTestCase
from .test_fields import FieldsTests
from .test_forms import FormsTestCase
from .test_formsets import (FormsFormsetTestCase, FormsetAsFooTests,
    TestIsBoundBehavior, TestEmptyFormSet)
from .test_input_formats import (LocalizedTimeTests, CustomTimeInputFormatsTests,
    SimpleTimeFormatTests, LocalizedDateTests, CustomDateInputFormatsTests,
    SimpleDateFormatTests, LocalizedDateTimeTests,
    CustomDateTimeInputFormatsTests, SimpleDateTimeFormatTests)
from .test_media import FormsMediaTestCase, StaticFormsMediaTestCase
from .tests import (TestTicket12510, TestTicket14567, ModelFormCallableModelDefault,
    FormsModelTestCase, RelatedModelFormTests)
from .test_regressions import FormsRegressionsTestCase
from .test_util import FormsUtilTestCase
from .test_validators import TestFieldWithValidators
from .test_widgets import (FormsWidgetTestCase, FormsI18NWidgetsTestCase,
    WidgetTests, LiveWidgetTests, ClearableFileInputTests)

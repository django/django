from django.db.models import Count, Func
from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango40Warning

from .models import Employee


class MissingAliasFunc(Func):
    template = '1'

    def get_group_by_cols(self):
        return []


class GetGroupByColsTest(SimpleTestCase):
    def test_missing_alias(self):
        msg = (
            '`alias=None` must be added to the signature of '
            'expressions.test_deprecation.MissingAliasFunc.get_group_by_cols().'
        )
        with self.assertRaisesMessage(RemovedInDjango40Warning, msg):
            Employee.objects.values(
                one=MissingAliasFunc(),
            ).annotate(cnt=Count('company_ceo_set'))

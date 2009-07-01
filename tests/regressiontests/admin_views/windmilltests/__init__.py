fixtures = ['admin-views-users.xml',
    'admin-views-colors.xml',
    'admin-views-fabrics.xml',
    'admin-views-unicode.xml',
    'multiple-child-classes',
    'admin-views-actions.xml',
    'string-primary-key.xml',
    'admin-views-person.xml']

# import os
# from django.test import windmill_tests as djangotest
# #from windmill.authoring import djangotest

from windmill.conf import global_settings
ADMIN_URL =  "%s/test_admin/admin" % global_settings.TEST_URL
#ADMIN_URL = 'http://localhost:8000/test_admin/admin/'
#['regressiontests/admin_views/fixtures/%s' % fix for fix in ]

#
# class TestProjectWindmillTest(djangotest.WindmillDjangoUnitTest):
#     fixtures = ['admin-views-users.xml', 'admin-views-colors.xml', 'admin-views-fabrics.xml', 'admin-views-unicode.xml',
#         'multiple-child-classes', 'admin-views-actions.xml', 'string-primary-key.xml', 'admin-views-person.xml']
#     #test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'windmilltests')
#     test_dir = os.path.dirname(os.path.abspath(__file__))
#     #test_dir = os.path.dirname(os.path.abspath(__file__))
#     browser = 'firefox'
#     test_url = 'http://localhost:8000/test_admin/admin/'
#     global_settings.TEST_URL = test_url
#
#     # def test_tryout(self):
#     #     pass
#
from windmill.authoring import WindmillTestClient
from django.test.utils import calling_func_name

# import functest
# functest.modules_passed = []
# functest.modules_failed = []
from primary import *

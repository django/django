#!/usr/bin/env sh
# - 60 second test subset, for security group to use prior to pushing commits
TEST_SET="admin_registration admin_util admin_validation admin_views backends cache csrf_tests file_storage inspectdb generic_inline_admin managers_regress middleware model_permalink modeladmin queryset_pickle serializers_regress signed_cookies_tests signing transactions_regress utils"
./runtests.py --settings=test_sqlite $TEST_SET

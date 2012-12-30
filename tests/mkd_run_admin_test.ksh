#!/bin/ksh

export DJANGO_LIVE_TEST_SERVER_ADDRESS=localhost:5150

python runtests.py --settings=test_sqlite admin_changelist
python runtests.py --settings=test_sqlite admin_custom_urls
python runtests.py --settings=test_sqlite admin_filters
python runtests.py --settings=test_sqlite admin_inlines
python runtests.py --settings=test_sqlite admin_ordering
python runtests.py --settings=test_sqlite admin_registration
python runtests.py --settings=test_sqlite admin_scripts
python runtests.py --settings=test_sqlite admin_util
python runtests.py --settings=test_sqlite admin_validation
python runtests.py --settings=test_sqlite admin_views
python runtests.py --settings=test_sqlite admin_widgets



import os
import sys

# Add project root
sys.path.insert(0, os.path.abspath("."))

# Set Django settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'

import django
django.setup()

import unittest

# Discover and run tests
loader = unittest.TestLoader()
suite = loader.discover('tests/views', pattern='test_sensitive_data.py')
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

if result.wasSuccessful():
    sys.exit(0)
else:
    sys.exit(1)
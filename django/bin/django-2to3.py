#!/usr/bin/env python

# This works exactly like 2to3, except that it uses Django's fixers rather
# than 2to3's built-in fixers.

import sys
from lib2to3.main import main

sys.exit(main("django.utils.2to3_fixes"))


from django.utils import unittest
from django.core.management import find_management_module
import sys
import os

class ManagementCommandTest(unittest.TestCase):

    def test_modules_from_different_setuptools_packages(self):
        """Test for ticket 18685. Check that multiple modules in the same package,
        installed from different setuptools packages, load their management commands
        correctly.
        """

        #Add the package directories to the sys path, like setuptools would do,
        #when running the 'develop' command via an egg-link
        sys.path.append(os.path.join(os.path.dirname(__file__), "project-A"))
        sys.path.append(os.path.join(os.path.dirname(__file__), "project-B"))

        module_A_path = find_management_module("mypackage.A")
        self.assertTrue(module_A_path.endswith("project-A/mypackage/A/management"), module_A_path)
        module_B_path = find_management_module("mypackage.B")
        self.assertTrue(module_B_path.endswith("project-B/mypackage/B/management"), module_B_path)

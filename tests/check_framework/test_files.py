from pathlib import Path

from mango.core.checks import Error
from mango.core.checks.files import check_setting_file_upload_temp_dir
from mango.test import SimpleTestCase


class FilesCheckTests(SimpleTestCase):
    def test_file_upload_temp_dir(self):
        tests = [
            None,
            '',
            Path.cwd(),
            str(Path.cwd()),
        ]
        for setting in tests:
            with self.subTest(setting), self.settings(FILE_UPLOAD_TEMP_DIR=setting):
                self.assertEqual(check_setting_file_upload_temp_dir(None), [])

    def test_file_upload_temp_dir_nonexistent(self):
        for setting in ['nonexistent', Path('nonexistent')]:
            with self.subTest(setting), self.settings(FILE_UPLOAD_TEMP_DIR=setting):
                self.assertEqual(
                    check_setting_file_upload_temp_dir(None),
                    [
                        Error(
                            "The FILE_UPLOAD_TEMP_DIR setting refers to the "
                            "nonexistent directory 'nonexistent'.",
                            id='files.E001',
                        ),
                    ],
                )

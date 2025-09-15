import shutil
import tempfile
from pathlib import Path

from django.db import connections
from django.test import TestCase


class SQLiteParallelCloneTests(TestCase):
    """
    Tests that cloned SQLite test databases respect the original
    directory when running tests in parallel.
    """

    def setUp(self):
        self.test_db_dir = Path(tempfile.mkdtemp()) / "db" / "default"
        self.test_db_dir.mkdir(parents=True, exist_ok=True)

        self.original_settings = None

        self.addCleanup(
            lambda: shutil.rmtree(self.test_db_dir.parent.parent, ignore_errors=True)
        )

    def tearDown(self):
        if self.original_settings is not None:
            conn = connections["default"]
            conn.settings_dict["NAME"] = self.original_settings["NAME"]
            conn.settings_dict["TEST"]["NAME"] = self.original_settings["TEST"]["NAME"]

    def test_clone_respects_directory(self):
        conn = connections["default"]
        self.original_settings = {
            "NAME": conn.settings_dict["NAME"],
            "TEST": {"NAME": conn.settings_dict["TEST"]["NAME"]},
        }

        conn.close()

        db_path = str(self.test_db_dir / "db.sqlite3")
        conn.settings_dict["NAME"] = db_path
        conn.settings_dict["TEST"]["NAME"] = str(self.test_db_dir / "test_db.sqlite3")

        clone = conn.creation.get_test_db_clone_settings(1)

        clone_path = Path(clone["NAME"])
        self.assertIn("db", clone_path.parts)
        self.assertIn("default", clone_path.parts)
        self.assertTrue(clone_path.name.startswith("db_1"))

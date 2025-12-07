import unittest


class NoDatabaseTests(unittest.TestCase):
    def test_nothing(self):
        pass


class DefaultDatabaseTests(NoDatabaseTests):
    databases = {"default"}


class DefaultDatabaseSerializedTests(NoDatabaseTests):
    databases = {"default"}
    serialized_rollback = True


class OtherDatabaseTests(NoDatabaseTests):
    databases = {"other"}


class AllDatabasesTests(NoDatabaseTests):
    databases = "__all__"

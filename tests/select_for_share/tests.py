import threading
import time
from django.db import (
    connection,
    transaction, OperationalError,
)
from django.test import (
    TransactionTestCase,
    skipUnlessDBFeature,
)

from .models import (
    City,
    Country,
    Person,
    PersonProfile,
)


class SelectForUpdateTests(TransactionTestCase):
    available_apps = ["select_for_share"]

    def setUp(self):
        # This is executed in autocommit mode so that code in
        # run_select_for_update can see this data.
        self.country1 = Country.objects.create(name="Belgium")
        self.country2 = Country.objects.create(name="France")
        self.city1 = City.objects.create(name="Liberchies", country=self.country1)
        self.city2 = City.objects.create(name="Samois-sur-Seine", country=self.country2)
        self.person = Person.objects.create(
            name="Reinhardt", born=self.city1, died=self.city2
        )
        self.person_profile = PersonProfile.objects.create(person=self.person)

        # We need another database connection in transaction to test that one
        # connection issuing a SELECT ... FOR UPDATE will block.
        self.new_connection = connection.copy()

    def has_for_share_sql(self, queries, **kwargs):
        # Examine the SQL that was executed to determine whether it
        # contains the 'SELECT..FOR SHARE' stanza.
        for_share_sql = connection.ops.for_share_sql(**kwargs)
        return for_share_sql in queries

    @skipUnlessDBFeature("has_select_for_share")
    def test_for_update_sql_generated(self):
        try:
            with transaction.atomic():
                """
                The backend's FOR UPDATE variant appears in
                generated SQL when select_for_update is invoked.
                """
                sql = Person.objects.select_for_share().query
                self.assertTrue(self.has_for_share_sql(str(sql)))
        except Exception:
            self.assertTrue(False)

    @skipUnlessDBFeature("has_select_for_share_nowait")
    def test_for_update_sql_generated_nowait(self):
        """
        The backend's FOR UPDATE NOWAIT variant appears in
        generated SQL when select_for_update is invoked.
        """
        try:
            with transaction.atomic():
                """
                The backend's FOR SHARE variant appears in
                generated SQL when select_for_share is invoked.
                """
                sql = Person.objects.select_for_share(nowait=True).query
                self.assertTrue(self.has_for_share_sql(str(sql), nowait=True))
        except Exception:
            self.assertTrue(False)

    @skipUnlessDBFeature("has_select_for_share", "supports_transactions")
    def test_for_update_requires_transaction(self):
        """
        A TransactionManagementError is raised
        when a select_for_share query is executed outside of a transaction.
        """
        msg = "select_for_share cannot be used outside of a transaction."
        with self.assertRaisesMessage(transaction.TransactionManagementError, msg):
            list(Person.objects.select_for_share())

    @skipUnlessDBFeature("supports_select_for_share_with_limit")
    def test_select_for_share_with_limit(self):
        """
        Use limit
        """
        other = Person.objects.create(name="Grappeli", born=self.city1, died=self.city2)
        with transaction.atomic():
            qs = list(Person.objects.order_by("pk").select_for_share()[1:2])
            self.assertEqual(qs[0], other)

    @skipUnlessDBFeature("has_select_for_share")
    @skipUnlessDBFeature("supports_transactions")
    def test_block(self):
        """
        A thread running a select_for_share
        and try select_for_update ,want error
        """
        self.get_share_lock()
        time.sleep(2)
        res = False
        with transaction.atomic():
            try:
                data = Person.objects.filter(name="Reinhardt").select_for_update(
                    nowait=True)
                list(data)
            except OperationalError:
                res = True
            self.assertTrue(res)

    @skipUnlessDBFeature("has_select_for_share", "supports_transactions")
    def test_raw_lock_not_available(self):
        """
        A thread running a select_for_update
        and try select_for_share, want error
        """
        self.get_write_lock()
        time.sleep(2)
        res = False
        with transaction.atomic():
            try:
                data = Person.objects.filter(name="Reinhardt").select_for_share(
                    nowait=True)
                list(data)
            except OperationalError:
                res = True
            self.assertTrue(res)

    @skipUnlessDBFeature("has_select_for_share")
    def test_select_for_share_with_get(self):
        """select for share with get"""
        with transaction.atomic():
            person = Person.objects.select_for_share().get(name="Reinhardt")
        self.assertEqual(person.name, "Reinhardt")

    def test_ordered_select_for_share(self):
        """
        Subqueries should respect ordering as an ORDER BY clause may be useful
        to specify a row locking order to prevent deadlocks (#27193).
        """
        with transaction.atomic():
            qs = Person.objects.filter(
                id__in=Person.objects.order_by("-id").select_for_share()
            )
            self.assertIn("ORDER BY", str(qs.query))

    def get_share_lock(self):
        """
            Start transaction and use select for share
        """

        def share_lock():
            with transaction.atomic():
                try:
                    data = Person.objects.filter(name="Reinhardt").select_for_share()
                    list(data)
                    time.sleep(5)
                except Exception:
                    pass

        job = threading.Thread(target=share_lock)
        job.setDaemon(True)
        job.start()

    def get_write_lock(self, nowait: bool = True):
        """
            Start transaction and use select for update
        """

        def writ_lock():
            with transaction.atomic():
                try:
                    data = Person.objects.filter(name="Reinhardt").select_for_update(
                        nowait=nowait)
                    list(data)
                    time.sleep(5)
                    return True
                except OperationalError:
                    return False

        job = threading.Thread(target=writ_lock)
        job.setDaemon(True)
        job.start()

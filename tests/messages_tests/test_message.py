from django.contrib.messages import constants, restrictions
from django.contrib.messages.restrictions import AmountRestriction, TimeRestriction
from django.contrib.messages.storage.base import Message
from django.test import TestCase

from .time_provider import TestTimeProvider


class MessageTest(TestCase):
    def setUp(self):
        self.tp = restrictions.time_provider = TestTimeProvider()

    def __check_active(self, msg, iterations):
        """
        Reads msg given amount of iterations, and after each read
        checks whether before each read message is active
        """
        for i in range(iterations):
            self.assertTrue(msg.active())
            msg.on_display()
        self.assertFalse(msg.active())
        msg.on_display()
        self.assertFalse(msg.active())

    def test_active_default(self):
        msg = Message(constants.INFO, "Test message")
        self.__check_active(msg, 1)

    def test_active_custom_one_amount_restriction(self):
        msg = Message(
            constants.INFO,
            "Test message",
            restrictions=[
                AmountRestriction(3),
            ],
        )
        self.__check_active(msg, 3)

    def test_active_custom_few_amount_restriction(self):
        msg = Message(
            constants.INFO,
            "Test message",
            restrictions=[AmountRestriction(x) for x in (2, 3, 5)],
        )
        self.__check_active(msg, 2)

    def test_active_custom_one_time_restriction(self):
        msg = Message(
            constants.INFO,
            "Test message",
            restrictions=[
                TimeRestriction(3),
            ],
        )

        def check_iter():
            for i in range(
                10
            ):  # iteration doesn't have direct impact for TimeRestriction
                self.assertTrue(msg.active())
                msg.on_display()

        check_iter()
        self.tp.set_act_time(3)
        check_iter()
        self.tp.set_act_time(4)
        self.assertFalse(msg.active())

    def test_mixed_restrictions(self):
        def get_restrictions():
            return [
                TimeRestriction(3),
                TimeRestriction(5),
                AmountRestriction(2),
                AmountRestriction(3),
            ]

        def get_msg():
            return Message(
                constants.INFO, "Test message", restrictions=get_restrictions()
            )

        msg = get_msg()
        for i in range(2):
            self.assertTrue(msg.active())
            msg.on_display()
        self.assertFalse(msg.active())

        msg = get_msg()
        self.assertTrue(msg.active())
        msg.on_display()
        self.assertTrue(msg.active())
        self.tp.set_act_time(4)
        self.assertFalse(msg.active())
        for i in range(10):
            self.assertFalse(msg.active())
            msg.on_display()

from django.test import TestCase

from models import Child1, Child2, Child3, Child4, Child5, Child6, Child7


class ManagersRegressionTests(TestCase):
    def test_managers(self):
        a1 = Child1.objects.create(name='fred', data='a1')
        a2 = Child1.objects.create(name='barney', data='a2')
        b1 = Child2.objects.create(name='fred', data='b1', value=1)
        b2 = Child2.objects.create(name='barney', data='b2', value=42)
        c1 = Child3.objects.create(name='fred', data='c1', comment='yes')
        c2 = Child3.objects.create(name='barney', data='c2', comment='no')
        d1 = Child4.objects.create(name='fred', data='d1')
        d2 = Child4.objects.create(name='barney', data='d2')
        e1 = Child5.objects.create(name='fred', comment='yes')
        e2 = Child5.objects.create(name='barney', comment='no')
        f1 = Child6.objects.create(name='fred', data='f1', value=42)
        f2 = Child6.objects.create(name='barney', data='f2', value=42)
        g1 = Child7.objects.create(name='fred')
        g2 = Child7.objects.create(name='barney')

        self.assertQuerysetEqual(Child1.manager1.all(), ["<Child1: a1>"])
        self.assertQuerysetEqual(Child1.manager2.all(), ["<Child1: a2>"])
        self.assertQuerysetEqual(Child1._default_manager.all(), ["<Child1: a1>"])

        self.assertQuerysetEqual(Child2._default_manager.all(), ["<Child2: b1>"])
        self.assertQuerysetEqual(Child2.restricted.all(), ["<Child2: b2>"])

        self.assertQuerysetEqual(Child3._default_manager.all(), ["<Child3: c1>"])
        self.assertQuerysetEqual(Child3.manager1.all(), ["<Child3: c1>"])
        self.assertQuerysetEqual(Child3.manager2.all(), ["<Child3: c2>"])

        # Since Child6 inherits from Child4, the corresponding rows from f1 and
        # f2 also appear here. This is the expected result.
        self.assertQuerysetEqual(Child4._default_manager.order_by('data'), [
                "<Child4: d1>",
                "<Child4: d2>",
                "<Child4: f1>",
                "<Child4: f2>"
            ]
        )
        self.assertQuerysetEqual(Child4.manager1.all(), [
                "<Child4: d1>",
                "<Child4: f1>"
            ]
        )
        self.assertQuerysetEqual(Child5._default_manager.all(), ["<Child5: fred>"])
        self.assertQuerysetEqual(Child6._default_manager.all(), ["<Child6: f1>"])
        self.assertQuerysetEqual(Child7._default_manager.order_by('name'), [
                "<Child7: barney>",
                "<Child7: fred>"
            ]
        )

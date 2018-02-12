from django.db import models


class PersonManager(models.Manager):

    def get_by_natural_key(self, lastname, firstname):
        return self.get(lastname=lastname, firstname=firstname)


class Person(models.Model):
    firstname = models.CharField(max_length=20)
    lastname = models.CharField(max_length=20)
    objects = PersonManager()

    def natural_key(self):
        return (self.lastname, self.firstname)

    def data(self):
        return (self.lastname, self.firstname)


class Customer(Person):
    cnum = models.IntegerField()

    def data(self):
        return super(Customer, self).data() + (self.cnum,)


class PremiumCustomer(Customer):
    level = models.IntegerField()

    def data(self):
        return super(PremiumCustomer, self).data() + (self.level,)


class Employee(Person):
    enum = models.IntegerField()

    def data(self):
        return super(Employee, self).data() + (self.enum,)

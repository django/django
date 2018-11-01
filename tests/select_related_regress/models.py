from django.db import models


class Building(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return "Building: %s" % self.name


class Device(models.Model):
    building = models.ForeignKey('Building', models.CASCADE)
    name = models.CharField(max_length=10)

    def __str__(self):
        return "device '%s' in building %s" % (self.name, self.building)


class Port(models.Model):
    device = models.ForeignKey('Device', models.CASCADE)
    port_number = models.CharField(max_length=10)

    def __str__(self):
        return "%s/%s" % (self.device.name, self.port_number)


class Connection(models.Model):
    start = models.ForeignKey(
        Port,
        models.CASCADE,
        related_name='connection_start',
        unique=True,
    )
    end = models.ForeignKey(
        Port,
        models.CASCADE,
        related_name='connection_end',
        unique=True,
    )

    def __str__(self):
        return "%s to %s" % (self.start, self.end)

# Another non-tree hierarchy that exercises code paths similar to the above
# example, but in a slightly different configuration.


class TUser(models.Model):
    name = models.CharField(max_length=200)


class Person(models.Model):
    user = models.ForeignKey(TUser, models.CASCADE, unique=True)


class Organizer(models.Model):
    person = models.ForeignKey(Person, models.CASCADE)


class Student(models.Model):
    person = models.ForeignKey(Person, models.CASCADE)


class Class(models.Model):
    org = models.ForeignKey(Organizer, models.CASCADE)


class Enrollment(models.Model):
    std = models.ForeignKey(Student, models.CASCADE)
    cls = models.ForeignKey(Class, models.CASCADE)

# Models for testing bug #8036.


class Country(models.Model):
    name = models.CharField(max_length=50)


class State(models.Model):
    name = models.CharField(max_length=50)
    country = models.ForeignKey(Country, models.CASCADE)


class ClientStatus(models.Model):
    name = models.CharField(max_length=50)


class Client(models.Model):
    name = models.CharField(max_length=50)
    state = models.ForeignKey(State, models.SET_NULL, null=True)
    status = models.ForeignKey(ClientStatus, models.CASCADE)


class SpecialClient(Client):
    value = models.IntegerField()

# Some model inheritance exercises


class Parent(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class Child(Parent):
    value = models.IntegerField()


class Item(models.Model):
    name = models.CharField(max_length=10)
    child = models.ForeignKey(Child, models.SET_NULL, null=True)

    def __str__(self):
        return self.name

# Models for testing bug #19870.


class Fowl(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class Hen(Fowl):
    pass


class Chick(Fowl):
    mother = models.ForeignKey(Hen, models.CASCADE)


class Base(models.Model):
    name = models.CharField(max_length=10)
    lots_of_text = models.TextField()

    class Meta:
        abstract = True


class A(Base):
    a_field = models.CharField(max_length=10)


class B(Base):
    b_field = models.CharField(max_length=10)


class C(Base):
    c_a = models.ForeignKey(A, models.CASCADE)
    c_b = models.ForeignKey(B, models.CASCADE)
    is_published = models.BooleanField(default=False)

import datetime

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Country(models.Model):
    # Table Column Fields
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Person(models.Model):
    # Table Column Fields
    name = models.CharField(max_length=128)
    person_country_id = models.IntegerField()

    # Relation Fields
    person_country = models.ForeignObject(
        Country,
        from_fields=['person_country_id'],
        to_fields=['id'],
        on_delete=models.CASCADE,
    )
    friends = models.ManyToManyField('self', through='Friendship', symmetrical=False)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Group(models.Model):
    # Table Column Fields
    name = models.CharField(max_length=128)
    group_country = models.ForeignKey(Country, models.CASCADE)
    members = models.ManyToManyField(Person, related_name='groups', through='Membership')

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Membership(models.Model):
    # Table Column Fields
    membership_country = models.ForeignKey(Country, models.CASCADE)
    date_joined = models.DateTimeField(default=datetime.datetime.now)
    invite_reason = models.CharField(max_length=64, null=True)
    person_id = models.IntegerField()
    group_id = models.IntegerField()

    # Relation Fields
    person = models.ForeignObject(
        Person,
        from_fields=['membership_country', 'person_id'],
        to_fields=['person_country_id', 'id'],
        on_delete=models.CASCADE,
    )
    group = models.ForeignObject(
        Group,
        from_fields=['membership_country', 'group_id'],
        to_fields=['group_country', 'id'],
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ('date_joined', 'invite_reason')

    def __str__(self):
        return "%s is a member of %s" % (self.person.name, self.group.name)


class Friendship(models.Model):
    # Table Column Fields
    from_friend_country = models.ForeignKey(Country, models.CASCADE, related_name="from_friend_country")
    from_friend_id = models.IntegerField()
    to_friend_country_id = models.IntegerField()
    to_friend_id = models.IntegerField()

    # Relation Fields
    from_friend = models.ForeignObject(
        Person,
        on_delete=models.CASCADE,
        from_fields=['from_friend_country', 'from_friend_id'],
        to_fields=['person_country_id', 'id'],
        related_name='from_friend')

    to_friend_country = models.ForeignObject(
        Country,
        from_fields=['to_friend_country_id'],
        to_fields=['id'],
        related_name='to_friend_country',
        on_delete=models.CASCADE,
    )

    to_friend = models.ForeignObject(
        Person,
        from_fields=['to_friend_country_id', 'to_friend_id'],
        to_fields=['person_country_id', 'id'],
        related_name='to_friend',
        on_delete=models.CASCADE,
    )

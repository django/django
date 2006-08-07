"""
34. Row Level Permissions

Row Level Permissions are permissions for a specific instance of an object instead of
all types of an object.
"""

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import RowLevelPermission, User

class Mineral(models.Model):
    name = models.CharField(maxlength=150)
    hardness = models.PositiveSmallIntegerField()
    
    class Meta:
        row_level_permissions = True
    
    def __str__(self):
        return self.name
    
API_TESTS = """
>>> from django.contrib.auth.models import RowLevelPermission, Permission, User, Group
>>> from django.contrib.contenttypes.models import ContentType
>>>

#Create objects to use
>>> quartz = Mineral(name="Quartz", hardness=7)
>>> quartz.save()
>>> user = User.objects.create_user('john', 'lennon@thebeatles.com', 'johnpassword')
>>> group = Group(name="groupTest")
>>> group.save()
>>> perm = Permission(name="Can mine", codename="mine_mineral", content_type=ContentType.objects.get_for_model(Mineral))
>>> perm.save()

#Tests manager create method using permission object for user
>>> rlp = RowLevelPermission.objects.create_row_level_permission(quartz, user, perm)
>>> rlp.owner
<User: john>
>>> rlp.model
<Mineral: Quartz>
>>> rlp.permission
<Permission: mineral | Can mine>
>>> user.row_level_permissions_owned.all()
[mineral | Can mine | user:john | mineral:Quartz]
>>> rlp.delete()

#Tests manager create method using permission object for group
>>> rlp = RowLevelPermission.objects.create_row_level_permission(quartz, group, perm)
>>> rlp.owner
<Group: groupTest>
>>> rlp.model
<Mineral: Quartz>
>>> rlp.permission
<Permission: mineral | Can mine>
>>> group.row_level_permissions_owned.all()
[mineral | Can mine | group:groupTest | mineral:Quartz]
>>> rlp.delete()
>>>

#Tests manager create method using permission codename
>>> rlp = RowLevelPermission.objects.create_row_level_permission(quartz, user, perm.codename)
>>> rlp.owner
<User: john>
>>> rlp.model
<Mineral: Quartz>
>>> rlp.permission
<Permission: mineral | Can mine>
>>> user.row_level_permissions_owned.all()
[mineral | Can mine | user:john | mineral:Quartz]
>>> rlp.delete()

#Test create using RLP init method
>>> rlp = RowLevelPermission(model_id=quartz.id, model_ct=ContentType.objects.get_for_model(Mineral), owner_id=user.id, owner_ct=ContentType.objects.get_for_model(User), permission=perm)
>>> rlp.save()
>>> rlp.owner
<User: john>
>>> rlp.model
<Mineral: Quartz>
>>> rlp.permission
<Permission: mineral | Can mine>
>>> user.row_level_permissions_owned.all()
[mineral | Can mine | user:john | mineral:Quartz]
>>> rlp.delete()

#Test loading
>>> rlp = RowLevelPermission.objects.create_row_level_permission(quartz, user, perm.codename)
>>> rlp.owner
<User: john>
>>> rlp.model
<Mineral: Quartz>
>>> quartz.row_level_permissions.all()
[mineral | Can mine | user:john | mineral:Quartz]
>>> user.row_level_permissions_owned.all()
[mineral | Can mine | user:john | mineral:Quartz]
>>> rlp.delete()

#Test duplicate
>>> rlp = RowLevelPermission.objects.create_row_level_permission(quartz, user, perm.codename)
>>> rlp = RowLevelPermission.objects.create_row_level_permission(quartz, user, perm.codename)
Traceback (most recent call last):
    ...
IntegrityError: columns model_ct_id, model_id, owner_id, owner_ct_id, permission_id are not unique
>>> rlp=user.row_level_permissions_owned.get(model_id=quartz.id)
>>> rlp.delete()

#Check Permission
>>> rlp = RowLevelPermission.objects.create_row_level_permission(quartz, user, perm.codename)
>>> user.has_perm(quartz._meta.app_label +"."+ perm.codename, quartz)
True
>>> perm2 = Permission(name="Can change", codename="change_mineral", content_type=ContentType.objects.get_for_model(Mineral))
>>> perm2.save()
>>> user.has_perm(quartz._meta.app_label +"."+ perm2.codename, quartz)
False
>>> user.user_permissions.add(perm2)
>>> user.save()
>>> user.user_permissions.all()
[<Permission: mineral | Can change>]
>>> user.has_perm(quartz._meta.app_label +"."+ perm2.codename, quartz)
True
>>> rlp2 = RowLevelPermission.objects.create_row_level_permission(quartz, user, perm2, negative=True)
>>> user.has_perm(quartz._meta.app_label +"."+ perm2.codename, quartz)
False
>>> rlp.delete()
>>> rlp2.delete()
>>> user.user_permissions.all().delete()

#Check Permission Group
>>> user.has_perm(quartz._meta.app_label +"."+ perm2.codename, quartz)
False
>>> user.groups.add(group)
>>> user.save()
>>> rlp = RowLevelPermission.objects.create_row_level_permission(quartz, group, perm)
>>> user.row_level_permissions_owned.all()
[]
>>> group.row_level_permissions_owned.all()
[mineral | Can mine | group:groupTest | mineral:Quartz]
>>> user.has_perm(quartz._meta.app_label +"."+ perm.codename, quartz)
True
>>> rlp.delete()
>>> user.row_level_permissions_owned.all()
[]
>>> group.row_level_permissions_owned.all()
[]
>>> user.has_perm(quartz._meta.app_label +"."+ perm.codename, quartz)
False


"""
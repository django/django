from .custom_permissions import CustomPermissionsUser
from .custom_user import (
    CustomUser, CustomUserWithoutIsActiveField, ExtensionUser,
)
from .invalid_models import CustomUserNonUniqueUsername
from .is_active import IsActiveTestUser1
from .minimal import MinimalUser
from .no_password import NoPasswordUser
from .uuid_pk import UUIDUser
from .with_foreign_key import CustomUserWithFK, Email
from .with_integer_username import IntegerUsernameUser
from .with_last_login_attr import UserWithDisabledLastLoginField

__all__ = (
    'CustomUser', 'CustomUserWithoutIsActiveField', 'CustomPermissionsUser',
    'CustomUserWithFK', 'Email', 'ExtensionUser', 'IsActiveTestUser1',
    'MinimalUser', 'NoPasswordUser', 'UUIDUser', 'CustomUserNonUniqueUsername',
    'IntegerUsernameUser', 'UserWithDisabledLastLoginField',
)

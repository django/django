from .custom_permissions import CustomPermissionsUser
from .custom_user import CustomUser, CustomUserWithoutIsActiveField, ExtensionUser
from .invalid_models import CustomUserNonUniqueUsername
from .is_active import IsActiveTestUser1
from .minimal import MinimalUser
from .no_password import NoPasswordUser
from .proxy import Proxy, UserProxy
from .uuid_pk import UUIDUser
from .with_custom_email_field import CustomEmailField
from .with_foreign_key import CustomUserWithFK, Email
from .with_integer_username import IntegerUsernameUser
from .with_last_login_attr import UserWithDisabledLastLoginField
from .with_many_to_many import CustomUserWithM2M, CustomUserWithM2MThrough, Organization
from .with_unique_constraint import CustomUserWithUniqueConstraint

__all__ = (
    "CustomEmailField",
    "CustomPermissionsUser",
    "CustomUser",
    "CustomUserNonUniqueUsername",
    "CustomUserWithFK",
    "CustomUserWithM2M",
    "CustomUserWithM2MThrough",
    "CustomUserWithUniqueConstraint",
    "CustomUserWithoutIsActiveField",
    "Email",
    "ExtensionUser",
    "IntegerUsernameUser",
    "IsActiveTestUser1",
    "MinimalUser",
    "NoPasswordUser",
    "Organization",
    "Proxy",
    "UUIDUser",
    "UserProxy",
    "UserWithDisabledLastLoginField",
)

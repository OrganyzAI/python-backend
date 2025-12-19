from enum import Enum


class UserRole(str, Enum):
    user = "user"
    admin = "admin"


class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    banned = "banned"

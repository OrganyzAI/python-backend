from enum import Enum


class EmailTokenStatus(str, Enum):
    active = "active"
    used = "used"
    expired = "expired"

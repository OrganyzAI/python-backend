from enum import Enum

class OTPType(str, Enum):
    password_reset = "password_reset"
    email_verification = "email_verification"
    signup_confirmation = "signup_confirmation"
    login_confirmation = "login_confirmation"

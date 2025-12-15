class Messages:
    AUTH = {
        "SUCCESS": {
            "USER_REGISTERED": "User registered",
            "USER_LOGGED_IN": "Logged in",
            "EMAIL_VERIFIED": "Email verified",
            "PASSWORD_RESET_EMAIL_SENT": "Password reset email sent",
            "PASSWORD_HAS_BEEN_RESET": "Password has been reset",
            "VERIFICATION_EMAIL_RESENT": "Verification email resent",
            "LOGGED_OUT": "Logged out",
        },
        "ERROR": {
            "EMAIL_AND_PASSWORD_REQUIRED": "Email and password are required",
            "INVALID_CREDENTIALS": "Invalid credentials",
            "USER_EXISTS": "A user with that email already exists",
            "TOKEN_REQUIRED": "Token is required",
            "EMAIL_REQUIRED": "Email is required",
            "INVALID_TOKEN": "Invalid token",
            "INVALID_TOKEN_SUBJECT": "Invalid token subject",
            "TOKEN_EXPIRED": "Token expired",
            "TOKEN_AND_PASSWORD_REQUIRED": "Token and new password are required",
        },
    }
    VALIDATION = {
        "PASSWORD_TOO_WEAK": "Password must be at least 8 characters long and include uppercase, lowercase, number, and special character",
    }
MSG = Messages()

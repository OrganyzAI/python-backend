class Messages:
    # Success messages
    SUCCESS = "Operation completed successfully"
    CREATED = "Resource created successfully"
    UPDATED = "Resource updated successfully"
    DELETED = "Resource deleted successfully"

    # Error messages
    NOT_FOUND = "Resource not found"
    ALREADY_EXISTS = "Resource already exists"
    UNAUTHORIZED = "Unauthorized access"
    FORBIDDEN = "Access forbidden"
    BAD_REQUEST = "Invalid request"
    INTERNAL_ERROR = "Internal server error"
    VALIDATION_ERROR = "Validation error"

    # User messages
    USER_CREATED = "User created successfully"
    USER_NOT_FOUND = "User not found"
    USER_UPDATED = "User updated successfully"
    USER_DELETED = "User deleted successfully"
    INVALID_CREDENTIALS = "Invalid credentials"

    # Rate limit
    RATE_LIMIT_EXCEEDED = "Rate limit exceeded. Please try again later"

    @staticmethod
    def custom(message: str) -> str:
        return message

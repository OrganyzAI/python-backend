import random
import string


def random_lower_string(length: int = 8) -> str:
    return "".join(random.choice(string.ascii_lowercase) for _ in range(length))


def random_email() -> str:
    return f"{random_lower_string()}@example.com"

from app.utils_helper.regex import RegexClass


def test_is_strong_password_true():
    assert RegexClass.is_strong_password("Aa1!aaaa") is True


def test_is_strong_password_false():
    assert RegexClass.is_strong_password("weakpass") is False

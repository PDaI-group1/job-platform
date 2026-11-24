import pytest

from matching.privacy import redact_contacts


class TestEmails:
    def test_simple_email(self):
        assert redact_contacts("contact sara.makinen@example.com today") == "contact [email] today"

    def test_email_with_plus(self):
        assert redact_contacts("send to user+tag@domain.fi") == "send to [email]"

    def test_multiple_emails(self):
        result = redact_contacts("a@b.com and c@d.org")
        assert result == "[email] and [email]"

    def test_email_at_start(self):
        assert redact_contacts("test@example.com is my email") == "[email] is my email"


class TestFinnishPhones:
    def test_mobile_with_spaces(self):
        assert redact_contacts("Call me at 040 123 4567") == "Call me at [phone]"

    def test_mobile_no_spaces(self):
        assert redact_contacts("0401234567") == "[phone]"

    def test_mobile_with_hyphens(self):
        assert redact_contacts("040-123-4567") == "[phone]"

    def test_landline(self):
        assert redact_contacts("09 1234 5678") == "[phone]"

    def test_other_prefix(self):
        assert redact_contacts("044 987 6543") == "[phone]"

    def test_parenthesised_area_code(self):
        assert redact_contacts("(040) 123 4567") == "[phone]"


class TestInternationalPhones:
    def test_finnish_international(self):
        assert redact_contacts("+358 40 1234567") == "[phone]"

    def test_finnish_international_no_spaces(self):
        assert redact_contacts("+35840123456") == "[phone]"

    def test_other_country(self):
        assert redact_contacts("+44 20 7946 0958") == "[phone]"


class TestNoContacts:
    def test_plain_text_unchanged(self):
        text = "Senior Python developer with 5 years of experience."
        assert redact_contacts(text) == text

    def test_year_not_matched(self):
        assert redact_contacts("worked there 2019–2024") == "worked there 2019–2024"

    def test_decimal_not_matched(self):
        assert redact_contacts("0.25 years") == "0.25 years"

    def test_version_number_not_matched(self):
        assert redact_contacts("Python 3.11") == "Python 3.11"


class TestMixed:
    def test_email_and_phone_in_same_text(self):
        text = "sara.makinen@example.com | +358 40 1234567"
        assert redact_contacts(text) == "[email] | [phone]"

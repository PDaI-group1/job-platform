"""
Contact detail redaction for CV text before sending to an LLM.

Only emails and phone numbers are redacted. Names are not touched.
"""

import re

# Standard email addresses
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# International format: +358 40 1234567, +1 234 567 8901, etc.
# Matches + followed by a country code and 6-12 more digits with optional spaces/hyphens.
_PHONE_INTL_RE = re.compile(r"\+\d{1,3}(?:[\s\-]?\d){6,12}")

# Finnish domestic format: 040 123 4567, 040-123-4567, 0401234567, 09 1234 5678.
# Starts at a word boundary to avoid matching digits inside larger numbers.
_PHONE_FI_RE = re.compile(r"(?<![.\d])0\d(?:[\s\-]?\d){6,9}(?![.\d])")

# Finnish domestic with parenthesised area code: (040) 123 4567.
_PHONE_FI_PAREN_RE = re.compile(r"\(0\d+\)[\s\-]?\d[\d\s\-]{5,}")


def redact_contacts(text: str) -> str:
    """Replace email addresses and phone numbers in *text* with placeholders.

    Emails are replaced with ``[email]``, phone numbers with ``[phone]``.
    The rest of the text is unchanged.

    Args:
        text: Plain text, e.g. a CV.

    Returns:
        Text with contact details redacted.
    """
    text = _EMAIL_RE.sub("[email]", text)
    text = _PHONE_INTL_RE.sub("[phone]", text)
    text = _PHONE_FI_RE.sub("[phone]", text)
    text = _PHONE_FI_PAREN_RE.sub("[phone]", text)
    return text

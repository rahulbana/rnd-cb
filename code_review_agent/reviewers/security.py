"""Security Review reviewer."""

from .base import Reviewer


class SecurityReviewer(Reviewer):
    """The Security Review perspective."""

    key = "security"
    title = "Security Review"
    guidance = (
        "Check for: SQL injection; command injection; path traversal; "
        "unsafe `pickle`; unsafe `yaml.load`; hardcoded passwords or API "
        "keys; weak hashing (MD5/SHA1 for secrets); `random` instead of "
        "`secrets`; missing JWT validation; missing authentication or "
        "authorization; CSRF; XSS; SSRF; open redirect; insecure "
        "deserialization; unsafe `eval()`/`exec()`; `subprocess(..., "
        "shell=True)`; insecure temp-file creation; and overly permissive "
        "file permissions."
    )

"""Per-recipient access codes for the public demo: cost control, not authentication."""

import hmac

from pydantic import BaseModel, ConfigDict

OPEN_LABEL = "open"
CODE_SEPARATOR = ","
LABEL_SEPARATOR = ":"


class AccessCodeError(ValueError):
    """Raised when the configured access codes cannot be read."""


def parse_access_codes(raw: str) -> dict[str, str]:
    """Read `code:label,code:label` into a mapping, rejecting anything ambiguous."""
    codes: dict[str, str] = {}

    for entry in raw.split(CODE_SEPARATOR):
        cleaned = entry.strip()
        if not cleaned:
            continue

        code, separator, label = cleaned.partition(LABEL_SEPARATOR)
        code, label = code.strip(), label.strip()
        if not separator or not code or not label:
            raise AccessCodeError(f"expected 'code:label', got {cleaned!r}")
        if code in codes:
            raise AccessCodeError(f"duplicate access code {code!r}")

        codes[code] = label

    if not codes:
        raise AccessCodeError("no access codes were configured")
    return codes


class AccessPolicy(BaseModel):
    """Who may spend tokens. No codes configured means the deployment is open."""

    model_config = ConfigDict(frozen=True)

    codes: dict[str, str] | None = None

    @classmethod
    def from_raw(cls, raw: str | None) -> "AccessPolicy":
        if raw is None or not raw.strip():
            return cls()
        return cls(codes=parse_access_codes(raw))

    @property
    def required(self) -> bool:
        return self.codes is not None

    def label_for(self, presented: str | None) -> str | None:
        """The recipient behind a code, or None when it is unknown or missing."""
        if self.codes is None:
            return OPEN_LABEL
        if not presented:
            return None

        offered = presented.strip().encode("utf-8")
        for code, label in self.codes.items():
            if hmac.compare_digest(offered, code.encode("utf-8")):
                return label
        return None

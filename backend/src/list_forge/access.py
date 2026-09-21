"""Per-recipient access codes for the public demo: cost control, not authentication."""

import hmac

from pydantic import BaseModel, ConfigDict, Field

OPEN_LABEL = "open"
CODE_SEPARATOR = ","
FIELD_SEPARATOR = ":"
MAX_FIELDS = 3


class AccessCodeError(ValueError):
    """Raised when the configured access codes cannot be read."""


class AccessGrant(BaseModel):
    """Who a code belongs to, and their own daily allowance when it differs from the default."""

    model_config = ConfigDict(frozen=True)

    label: str = Field(min_length=1)
    daily_runs: int | None = Field(default=None, gt=0)


def parse_access_codes(raw: str) -> dict[str, AccessGrant]:
    """Read `code:label` or `code:label:runs` entries, rejecting anything ambiguous."""
    grants: dict[str, AccessGrant] = {}

    for entry in raw.split(CODE_SEPARATOR):
        cleaned = entry.strip()
        if not cleaned:
            continue

        fields = [field.strip() for field in cleaned.split(FIELD_SEPARATOR)]
        if len(fields) < 2 or len(fields) > MAX_FIELDS or not all(fields):
            raise AccessCodeError(f"expected 'code:label' or 'code:label:runs', got {cleaned!r}")

        code, label = fields[0], fields[1]
        if code in grants:
            raise AccessCodeError(f"duplicate access code {code!r}")

        grants[code] = AccessGrant(label=label, daily_runs=_runs(fields, cleaned))

    if not grants:
        raise AccessCodeError("no access codes were configured")
    return grants


def _runs(fields: list[str], entry: str) -> int | None:
    if len(fields) < MAX_FIELDS:
        return None
    try:
        runs = int(fields[2])
    except ValueError as error:
        raise AccessCodeError(f"daily runs must be a whole number in {entry!r}") from error
    if runs <= 0:
        raise AccessCodeError(f"daily runs must be positive in {entry!r}")
    return runs


class AccessPolicy(BaseModel):
    """Who may spend tokens. No codes configured means the deployment is open."""

    model_config = ConfigDict(frozen=True)

    codes: dict[str, AccessGrant] | None = None

    @classmethod
    def from_raw(cls, raw: str | None) -> "AccessPolicy":
        if raw is None or not raw.strip():
            return cls()
        return cls(codes=parse_access_codes(raw))

    @property
    def required(self) -> bool:
        return self.codes is not None

    def grant_for(self, presented: str | None) -> AccessGrant | None:
        """The recipient behind a code, or None when it is unknown or missing."""
        if self.codes is None:
            return AccessGrant(label=OPEN_LABEL)
        if not presented:
            return None

        offered = presented.strip().encode("utf-8")
        for code, grant in self.codes.items():
            if hmac.compare_digest(offered, code.encode("utf-8")):
                return grant
        return None

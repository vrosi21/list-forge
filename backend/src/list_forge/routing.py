"""The trust policy: what a generated text is allowed to become."""

from collections.abc import Sequence

from list_forge.models import Finding, GeneratedCopy, Status


def route(output: GeneratedCopy | None, findings: Sequence[Finding]) -> Status:
    """No usable output fails; anything a check flagged goes to a person; the rest is approved."""
    if output is None:
        return Status.FAILED
    if findings:
        return Status.NEEDS_REVIEW
    return Status.APPROVED

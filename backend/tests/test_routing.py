import pytest

from fakes import VALID_COPY
from list_forge.models import CheckName, Finding, GeneratedCopy, Severity, Status
from list_forge.routing import route

COPY = GeneratedCopy.model_validate(VALID_COPY)


def finding(severity: Severity = Severity.WARN) -> Finding:
    return Finding(
        check=CheckName.NUMBER,
        field="description",
        start=0,
        end=3,
        text="120",
        message="120 is not in the product data",
        severity=severity,
    )


@pytest.mark.parametrize(
    ("output", "findings", "expected"),
    [
        pytest.param(COPY, [], Status.APPROVED, id="clean-copy-is-approved"),
        pytest.param(COPY, [finding()], Status.NEEDS_REVIEW, id="a-warning-needs-a-person"),
        pytest.param(
            COPY, [finding(Severity.BLOCK)], Status.NEEDS_REVIEW, id="a-block-needs-a-person"
        ),
        pytest.param(None, [], Status.FAILED, id="no-output-is-a-failure"),
    ],
)
def test_routing(output: GeneratedCopy | None, findings: list[Finding], expected: Status) -> None:
    assert route(output, findings) is expected


def test_approval_never_happens_while_a_finding_stands() -> None:
    assert route(COPY, [finding(), finding(Severity.BLOCK)]) is Status.NEEDS_REVIEW

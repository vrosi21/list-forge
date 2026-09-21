import pytest

from list_forge.access import (
    OPEN_LABEL,
    AccessCodeError,
    AccessGrant,
    AccessPolicy,
    parse_access_codes,
)


class TestParsing:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            pytest.param("a1:alice", {"a1": AccessGrant(label="alice")}, id="one-pair"),
            pytest.param(
                "a1:alice,b2:bob",
                {"a1": AccessGrant(label="alice"), "b2": AccessGrant(label="bob")},
                id="two-pairs",
            ),
            pytest.param(
                " a1 : alice , b2 : bob ",
                {"a1": AccessGrant(label="alice"), "b2": AccessGrant(label="bob")},
                id="padded",
            ),
            pytest.param(
                "a1:alice,,b2:bob",
                {"a1": AccessGrant(label="alice"), "b2": AccessGrant(label="bob")},
                id="empty-entry",
            ),
            pytest.param(
                "a1:alice:100",
                {"a1": AccessGrant(label="alice", daily_runs=100)},
                id="own-limit",
            ),
            pytest.param(
                "a1:dev:100,b2:recruiter",
                {
                    "a1": AccessGrant(label="dev", daily_runs=100),
                    "b2": AccessGrant(label="recruiter"),
                },
                id="mixed",
            ),
        ],
    )
    def test_it_reads_entries(self, raw: str, expected: dict[str, AccessGrant]) -> None:
        assert parse_access_codes(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            pytest.param("", id="empty"),
            pytest.param("   ", id="blank"),
            pytest.param("a1", id="no-label"),
            pytest.param("a1:", id="empty-label"),
            pytest.param(":alice", id="empty-code"),
            pytest.param("a1:alice,a1:bob", id="duplicate-code"),
            pytest.param("a1:alice:many", id="limit-not-a-number"),
            pytest.param("a1:alice:0", id="limit-zero"),
            pytest.param("a1:alice:-5", id="limit-negative"),
            pytest.param("a1:alice:", id="limit-empty"),
            pytest.param("a1:alice:10:extra", id="too-many-fields"),
        ],
    )
    def test_it_rejects_anything_ambiguous(self, raw: str) -> None:
        with pytest.raises(AccessCodeError):
            parse_access_codes(raw)


class TestPolicy:
    def test_no_codes_means_open(self) -> None:
        policy = AccessPolicy.from_raw(None)

        assert policy.required is False
        assert policy.grant_for(None) == AccessGrant(label=OPEN_LABEL)

    def test_a_blank_setting_means_open(self) -> None:
        assert AccessPolicy.from_raw("  ").required is False

    @pytest.mark.parametrize(
        ("presented", "expected"),
        [
            pytest.param("a1", AccessGrant(label="alice"), id="known"),
            pytest.param(" a1 ", AccessGrant(label="alice"), id="known-padded"),
            pytest.param("b2", AccessGrant(label="bob", daily_runs=100), id="own-limit"),
            pytest.param("nope", None, id="unknown"),
            pytest.param("", None, id="empty"),
            pytest.param(None, None, id="missing"),
            pytest.param("A1", None, id="case-sensitive"),
        ],
    )
    def test_it_resolves_a_code_to_its_grant(
        self, presented: str | None, expected: AccessGrant | None
    ) -> None:
        policy = AccessPolicy.from_raw("a1:alice,b2:bob:100")

        assert policy.grant_for(presented) == expected

import pytest

from list_forge.access import OPEN_LABEL, AccessCodeError, AccessPolicy, parse_access_codes


class TestParsing:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            pytest.param("a1:alice", {"a1": "alice"}, id="one-pair"),
            pytest.param("a1:alice,b2:bob", {"a1": "alice", "b2": "bob"}, id="two-pairs"),
            pytest.param(" a1 : alice , b2 : bob ", {"a1": "alice", "b2": "bob"}, id="padded"),
            pytest.param("a1:alice,,b2:bob", {"a1": "alice", "b2": "bob"}, id="empty-entry"),
        ],
    )
    def test_it_reads_pairs(self, raw: str, expected: dict[str, str]) -> None:
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
        ],
    )
    def test_it_rejects_anything_ambiguous(self, raw: str) -> None:
        with pytest.raises(AccessCodeError):
            parse_access_codes(raw)


class TestPolicy:
    def test_no_codes_means_open(self) -> None:
        policy = AccessPolicy.from_raw(None)

        assert policy.required is False
        assert policy.label_for(None) == OPEN_LABEL

    def test_a_blank_setting_means_open(self) -> None:
        assert AccessPolicy.from_raw("  ").required is False

    @pytest.mark.parametrize(
        ("presented", "expected"),
        [
            pytest.param("a1", "alice", id="known"),
            pytest.param(" a1 ", "alice", id="known-padded"),
            pytest.param("b2", "bob", id="second-known"),
            pytest.param("nope", None, id="unknown"),
            pytest.param("", None, id="empty"),
            pytest.param(None, None, id="missing"),
            pytest.param("A1", None, id="case-sensitive"),
        ],
    )
    def test_it_resolves_a_code_to_its_recipient(
        self, presented: str | None, expected: str | None
    ) -> None:
        policy = AccessPolicy.from_raw("a1:alice,b2:bob")

        assert policy.label_for(presented) == expected

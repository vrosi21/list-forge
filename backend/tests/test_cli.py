from datetime import UTC, datetime
from pathlib import Path

import pytest

from list_forge.cli import format_usage, main
from list_forge.config import Settings
from list_forge.models import UsageSummary

AT = datetime(2026, 11, 6, 17, 30, tzinfo=UTC)


def summary(
    label: str, batches: int = 1, regenerations: int = 0, products: int = 5
) -> UsageSummary:
    return UsageSummary(
        label=label,
        batches=batches,
        regenerations=regenerations,
        products=products,
        last_run_at=AT,
    )


class TestFormatUsage:
    def test_no_runs_is_said_plainly(self) -> None:
        assert format_usage([]) == ["no runs recorded"]

    @pytest.mark.parametrize(
        ("row", "expected"),
        [
            (summary("alice"), ["alice", "1", "0", "5", "2026-11-06", "17:30"]),
            (summary("bob", 3, 2, 12), ["bob", "3", "2", "12", "2026-11-06", "17:30"]),
        ],
    )
    def test_each_code_gets_one_row(self, row: UsageSummary, expected: list[str]) -> None:
        header, line = format_usage([row])

        assert header.split()[:4] == ["code", "batches", "regenerations", "products"]
        assert line.split() == expected

    def test_columns_line_up(self) -> None:
        lines = format_usage([summary("a"), summary("a-much-longer-label", 10, 10, 100)])

        assert len({len(line) for line in lines[1:]}) == 1


def test_the_usage_command_reads_the_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = Settings(_env_file=None, database_path=tmp_path / "empty.db")
    monkeypatch.setattr("list_forge.cli.get_settings", lambda: settings)

    assert main(["usage", "--days", "7"]) == 0
    assert capsys.readouterr().out.strip() == "no runs recorded"

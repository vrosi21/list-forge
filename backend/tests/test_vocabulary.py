import pytest

from list_forge.vocabulary import build_vocabulary, normalise

VOCABULARY = build_vocabulary(
    entities=["amethyst", "quartz", "rose quartz", "clear quartz", "tiger's eye", "gold", "purple"],
    origins=["brazil", "sri lanka"],
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("  Rose   Quartz ", "rose quartz", id="whitespace-and-case"),
        pytest.param("Tiger’s Eye", "tiger's eye", id="curly-apostrophe"),
    ],
)
def test_terms_are_normalised_for_comparison(raw: str, expected: str) -> None:
    assert normalise(raw) == expected


def test_the_longest_matching_term_wins() -> None:
    matches = VOCABULARY.find_entities("A rose quartz sphere")

    assert [match.term for match in matches] == ["rose quartz"]


def test_a_narrower_mention_is_still_found() -> None:
    matches = VOCABULARY.find_entities("Cut from quartz")

    assert [match.term for match in matches] == ["quartz"]


@pytest.mark.parametrize(
    "text",
    ["tiger's eye beads", "tigers eye beads", "Tiger’s Eye beads", "TIGER'S EYE beads"],
)
def test_apostrophe_and_case_variants_all_match(text: str) -> None:
    assert [match.term for match in VOCABULARY.find_entities(text)] == ["tiger's eye"]


def test_plurals_match_the_singular_term() -> None:
    assert [match.term for match in VOCABULARY.find_entities("two amethysts")] == ["amethyst"]


def test_matches_carry_the_span_of_the_original_text() -> None:
    text = "A single amethyst point"

    match = VOCABULARY.find_entities(text)[0]

    assert text[match.start : match.end] == "amethyst"


def test_a_word_inside_another_word_is_not_a_match() -> None:
    assert VOCABULARY.find_entities("goldsmith") == []


def test_origins_are_matched_separately_from_entities() -> None:
    assert [match.term for match in VOCABULARY.find_origins("mined in Brazil")] == ["brazil"]
    assert VOCABULARY.find_entities("mined in Brazil") == []


def test_extending_adds_catalogue_terms_without_losing_the_originals() -> None:
    extended = VOCABULARY.extend(entities=["Labradorite"], origins=["Morocco"])

    assert [match.term for match in extended.find_entities("labradorite strand")] == ["labradorite"]
    assert [match.term for match in extended.find_origins("from morocco")] == ["morocco"]
    assert [match.term for match in extended.find_entities("amethyst")] == ["amethyst"]

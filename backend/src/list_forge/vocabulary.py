"""The words the content checks are able to recognise.

A check can only catch a term it knows, so this list is the reach of the entity and
origin checks. It is compiled once and matched against every generated field.
"""

import re
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CURLY_APOSTROPHE = chr(0x2019)
APOSTROPHES = f"['{CURLY_APOSTROPHE}]?"
WHITESPACE = re.compile(r"\s+")


class VocabularyError(ValueError):
    """Raised when the vocabulary file cannot be read."""


@dataclass(frozen=True)
class Match:
    term: str
    start: int
    end: int


@dataclass(frozen=True)
class Vocabulary:
    entities: tuple[str, ...]
    origins: tuple[str, ...]
    ambiguous: frozenset[str] = frozenset()
    origin_aliases: tuple[tuple[str, str], ...] = ()

    def find_entities(self, text: str) -> list[Match]:
        return _find(self.entities, text)

    def find_origins(self, text: str) -> list[Match]:
        """Adjective forms resolve to the place: 'Moroccan' is a claim about Morocco."""
        aliases = dict(self.origin_aliases)
        matches = _find((*self.origins, *aliases), text)
        return [
            Match(term=aliases.get(match.term, match.term), start=match.start, end=match.end)
            for match in matches
        ]

    def extend(self, entities: Iterable[str] = (), origins: Iterable[str] = ()) -> "Vocabulary":
        """A copy that also recognises terms taken from the catalogue being processed."""
        return Vocabulary(
            entities=_merge(self.entities, entities),
            origins=_merge(self.origins, origins),
            ambiguous=self.ambiguous,
            origin_aliases=self.origin_aliases,
        )

    def is_ambiguous(self, term: str) -> bool:
        """True for words that are colours in one sentence and plain adjectives in the next."""
        return term in self.ambiguous


def normalise(term: str) -> str:
    """Lowercase, straighten apostrophes, collapse whitespace: the comparison form."""
    return WHITESPACE.sub(" ", term.replace(CURLY_APOSTROPHE, "'").strip().lower())


def build_vocabulary(
    entities: Iterable[str],
    origins: Iterable[str],
    ambiguous: Iterable[str] = (),
    origin_aliases: Mapping[str, str] | None = None,
) -> Vocabulary:
    return Vocabulary(
        entities=_merge((), entities),
        origins=_merge((), origins),
        ambiguous=frozenset(normalise(term) for term in ambiguous),
        origin_aliases=tuple(
            (normalise(alias), normalise(origin))
            for alias, origin in sorted((origin_aliases or {}).items())
        ),
    )


def load_vocabulary(path: Path) -> Vocabulary:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except OSError as error:
        raise VocabularyError(f"{path.name}: {error}") from error
    except tomllib.TOMLDecodeError as error:
        raise VocabularyError(f"{path.name}: {error}") from error

    entities = [
        *_strings(data, "stones", path),
        *_strings(data, "colours", path),
        *_strings(data, "materials", path),
    ]
    aliases = data.get("origin_aliases", {})
    if not isinstance(aliases, dict) or not all(
        isinstance(value, str) for value in aliases.values()
    ):
        raise VocabularyError(f"{path.name}: origin_aliases must map a word to a place")

    return build_vocabulary(
        entities,
        _strings(data, "origins", path),
        _strings(data, "ambiguous", path),
        {str(alias): str(origin) for alias, origin in aliases.items()},
    )


def _strings(data: dict[str, object], key: str, path: Path) -> list[str]:
    values = data.get(key, [])
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise VocabularyError(f"{path.name}: {key} must be a list of strings")
    return [str(value) for value in values]


def _merge(existing: tuple[str, ...], extra: Iterable[str]) -> tuple[str, ...]:
    terms = {normalise(term) for term in (*existing, *extra) if normalise(term)}
    return tuple(sorted(terms, key=lambda term: (-len(term), term)))


def _find(terms: tuple[str, ...], text: str) -> list[Match]:
    """Longest terms first, so 'rose quartz' wins over 'quartz' at the same position."""
    if not terms:
        return []
    pattern = _compile(terms)
    canonical = _canonical_forms(terms)
    matches = []
    for match in pattern.finditer(text):
        term = canonical.get(normalise(match.group(0)))
        if term is not None:
            matches.append(Match(term=term, start=match.start(), end=match.end()))
    return matches


@lru_cache(maxsize=16)
def _canonical_forms(terms: tuple[str, ...]) -> dict[str, str]:
    """Every spelling a term can be matched as, mapped back to the term itself."""
    forms: dict[str, str] = {}
    for term in terms:
        plain = term.replace("'", "")
        for variant in (term, f"{term}s", plain, f"{plain}s"):
            forms.setdefault(variant, term)
    return forms


@lru_cache(maxsize=16)
def _compile(terms: tuple[str, ...]) -> re.Pattern[str]:
    alternatives = "|".join(_term_regex(term) for term in terms)
    return re.compile(rf"\b({alternatives})s?\b", re.IGNORECASE)


def _term_regex(term: str) -> str:
    words = [re.escape(word).replace("'", APOSTROPHES) for word in term.split(" ")]
    return r"\s+".join(words)

"""The words the content checks are able to recognise.

A check can only catch a term it knows, so this list is the reach of the entity and
origin checks. It is compiled once and matched against every generated field.
"""

import re
import tomllib
from collections.abc import Iterable
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

    def find_entities(self, text: str) -> list[Match]:
        return _find(self.entities, text)

    def find_origins(self, text: str) -> list[Match]:
        return _find(self.origins, text)

    def extend(self, entities: Iterable[str] = (), origins: Iterable[str] = ()) -> "Vocabulary":
        """A copy that also recognises terms taken from the catalogue being processed."""
        return Vocabulary(
            entities=_merge(self.entities, entities),
            origins=_merge(self.origins, origins),
        )


def normalise(term: str) -> str:
    """Lowercase, straighten apostrophes, collapse whitespace: the comparison form."""
    return WHITESPACE.sub(" ", term.replace(CURLY_APOSTROPHE, "'").strip().lower())


def build_vocabulary(entities: Iterable[str], origins: Iterable[str]) -> Vocabulary:
    return Vocabulary(entities=_merge((), entities), origins=_merge((), origins))


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
    return build_vocabulary(entities, _strings(data, "origins", path))


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

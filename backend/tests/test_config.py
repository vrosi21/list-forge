import pytest
from pydantic import ValidationError

from list_forge.config import ConfigurationError, Settings

KEY = "gsk-not-a-real-key"


def settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, GROQ_API_KEY=KEY, **overrides)


def test_the_api_key_never_appears_in_a_representation() -> None:
    rendered = f"{settings()!r} {settings().model_dump()}"

    assert KEY not in rendered


def test_the_api_key_is_returned_when_present() -> None:
    assert settings().require_llm_api_key().get_secret_value() == KEY


def test_a_missing_api_key_fails_before_any_request_is_attempted() -> None:
    with pytest.raises(ConfigurationError, match="GROQ_API_KEY"):
        Settings(_env_file=None).require_llm_api_key()


def test_generation_params_mirror_the_settings() -> None:
    params = settings(llm_model="openai/gpt-oss-120b", temperature=0.2).generation_params()

    assert params.model == "openai/gpt-oss-120b"
    assert params.temperature == 0.2
    assert params.reasoning_effort == "low"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("temperature", 2.5),
        ("max_concurrency", 0),
        ("request_timeout_s", 0),
        ("max_content_attempts", 99),
    ],
)
def test_out_of_range_settings_are_refused(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        settings(**{field: value})

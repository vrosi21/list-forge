"""Application settings, read once from the environment."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from list_forge.access import AccessPolicy
from list_forge.models import GenerationParams, ReasoningEffort
from list_forge.prompts import DEFAULT_PROMPT_VERSION, PROMPT_VERSIONS

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class ConfigurationError(RuntimeError):
    """Raised when a setting is needed but was never provided."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    llm_api_key: SecretStr | None = Field(default=None, validation_alias="GROQ_API_KEY")
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "openai/gpt-oss-20b"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    reasoning_effort: ReasoningEffort | None = "low"
    max_completion_tokens: int = Field(default=1500, gt=0)

    max_concurrency: int = Field(default=3, gt=0, le=32)
    max_transport_attempts: int = Field(default=5, gt=0, le=10)
    max_content_attempts: int = Field(default=3, gt=0, le=10)
    request_timeout_s: float = Field(default=30.0, gt=0)
    backoff_base_s: float = Field(default=1.0, gt=0)
    backoff_cap_s: float = Field(default=30.0, gt=0)

    max_upload_bytes: int = Field(default=1_000_000, gt=0)

    prompt_version: str = DEFAULT_PROMPT_VERSION

    demo_codes: SecretStr | None = None
    demo_max_rows: int | None = Field(default=None, gt=0)
    demo_daily_batches_per_code: int | None = Field(default=None, gt=0)
    requests_per_minute_per_ip: int | None = Field(default=None, gt=0)
    trust_proxy_headers: bool = False

    brands_dir: Path = BACKEND_DIR / "brands"
    data_dir: Path = REPO_ROOT / "data"
    output_dir: Path = BACKEND_DIR / "out"
    database_path: Path = BACKEND_DIR / "listforge.db"
    frontend_origin: str = "http://localhost:3000"

    @field_validator("prompt_version")
    @classmethod
    def _known_prompt_version(cls, value: str) -> str:
        if value not in PROMPT_VERSIONS:
            known = ", ".join(sorted(PROMPT_VERSIONS))
            raise ValueError(f"unknown prompt version {value!r}; known: {known}")
        return value

    @property
    def vocabulary_path(self) -> Path:
        return self.brands_dir / "vocab.toml"

    def require_llm_api_key(self) -> SecretStr:
        """The API key, or a clear failure before any request is attempted."""
        if self.llm_api_key is None:
            raise ConfigurationError("GROQ_API_KEY is not set")
        return self.llm_api_key

    def access_policy(self) -> AccessPolicy:
        """Parsed once at startup, so a malformed code list fails before any request."""
        raw = self.demo_codes.get_secret_value() if self.demo_codes else None
        return AccessPolicy.from_raw(raw)

    def generation_params(self) -> GenerationParams:
        return GenerationParams(
            model=self.llm_model,
            temperature=self.temperature,
            reasoning_effort=self.reasoning_effort,
            max_completion_tokens=self.max_completion_tokens,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Settings for the running process. Constructed once, cached afterwards."""
    return Settings()

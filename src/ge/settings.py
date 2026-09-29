"""Secrets and contact strings from .env (CLAUDE.md rule 10). Never print or log them."""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from ge.config import REPO_ROOT


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # NWS requires an identifying User-Agent; the Wikidata client reuses it (approved 2026-09-29).
    nws_user_agent: SecretStr

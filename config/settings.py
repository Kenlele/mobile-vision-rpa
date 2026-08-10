"""
config/settings.py
Global configuration settings for Mobile Vision RPA.
"""

import os
import configparser
from pydantic import BaseModel, Field


def _get_ini_value(section: str, key: str, fallback: str = "") -> str:
    """Read value from root config.ini if file exists and key is non-empty."""
    ini_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")
    if os.path.exists(ini_path):
        parser = configparser.ConfigParser()
        try:
            parser.read(ini_path, encoding="utf-8")
            if parser.has_option(section, key):
                val = parser.get(section, key).strip()
                if val:
                    return val
        except Exception:
            pass
    return fallback


def _get_provider() -> str:
    return _get_ini_value("LLM", "provider") or os.getenv("LLM_PROVIDER", "gemini")


def _get_api_key() -> str:
    provider = _get_provider()
    if provider == "openai":
        return _get_ini_value("LLM", "openai_api_key") or os.getenv("OPENAI_API_KEY", "")
    return (_get_ini_value("LLM", "gemini_api_key") or
            _get_ini_value("LLM", "openai_api_key") or
            os.getenv("GEMINI_API_KEY", os.getenv("OPENAI_API_KEY", "")))


def _get_model_name() -> str:
    return _get_ini_value("LLM", "model_name") or os.getenv("LLM_MODEL", "gemini-2.5-flash")


class LLMSettings(BaseModel):
    """Vision LLM API configuration."""
    provider: str = Field(default_factory=_get_provider)
    api_key: str = Field(default_factory=_get_api_key)
    model_name: str = Field(default_factory=_get_model_name)
    temperature: float = 0.1
    max_tokens: int = 1000


class DriverSettings(BaseModel):
    """Target device driver configuration."""
    driver_type: str = Field(default_factory=lambda: _get_ini_value("DRIVER", "driver_type") or "ios")
    ios_udid: str = Field(default_factory=lambda: _get_ini_value("DRIVER", "udid") or "booted")
    screen_width: int = 1179
    screen_height: int = 2556


class Settings(BaseModel):
    """Global configuration wrapper."""
    ocr_confidence_threshold: float = 0.5
    llm: LLMSettings = Field(default_factory=LLMSettings)
    driver: DriverSettings = Field(default_factory=DriverSettings)
    debug_mode: bool = True
    output_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "debug_output")


# Singleton settings instance
settings = Settings()


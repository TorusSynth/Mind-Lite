import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LlmConfig:
    active_provider: str = "lmstudio"
    active_model: str = "lmstudio:local"
    openrouter_api_key: str = ""
    lmstudio_url: str = "http://localhost:1234"
    recently_used: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_provider": self.active_provider,
            "active_model": self.active_model,
            "openrouter_api_key": self.openrouter_api_key,
            "lmstudio_url": self.lmstudio_url,
            "recently_used": self.recently_used,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LlmConfig":
        return cls(
            active_provider=data.get("active_provider", "lmstudio"),
            active_model=data.get("active_model", "lmstudio:local"),
            openrouter_api_key=data.get("openrouter_api_key", ""),
            lmstudio_url=data.get("lmstudio_url", "http://localhost:1234"),
            recently_used=data.get("recently_used", []),
        )


def _get_config_path() -> Path:
    base = os.getenv("MIND_LITE_STATE_FILE", ".mind_lite/state.json")
    config_dir = Path(base).parent
    return config_dir / "llm_config.json"


def get_llm_config() -> LlmConfig:
    config_path = _get_config_path()
    if config_path.exists():
        try:
            with open(config_path) as f:
                data = json.load(f)
            return LlmConfig.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            pass

    env_api_key = os.getenv("OPENROUTER_API_KEY", "")
    env_lmstudio_url = os.getenv("MIND_LITE_LMSTUDIO_URL", "http://localhost:1234")
    
    return LlmConfig(
        active_provider="lmstudio",
        active_model="lmstudio:local",
        openrouter_api_key=env_api_key,
        lmstudio_url=env_lmstudio_url,
        recently_used=[],
    )


def save_llm_config(config: LlmConfig) -> None:
    config_path = _get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, "w") as f:
        json.dump(config.to_dict(), f, indent=2)


def add_to_recently_used(config: LlmConfig, provider: str, model: str) -> LlmConfig:
    new_entry = {"provider": provider, "model": model}
    recent = [r for r in config.recently_used if r != new_entry]
    recent.insert(0, new_entry)
    recent = recent[:5]
    
    return LlmConfig(
        active_provider=config.active_provider,
        active_model=config.active_model,
        openrouter_api_key=config.openrouter_api_key,
        lmstudio_url=config.lmstudio_url,
        recently_used=recent,
    )

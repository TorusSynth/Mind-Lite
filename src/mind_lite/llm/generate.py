from typing import Any

from mind_lite.llm.config import LlmConfig, get_llm_config, save_llm_config, add_to_recently_used
from mind_lite.llm.models import get_provider_for_model
from mind_lite.llm.lmstudio import call_lmstudio
from mind_lite.llm.openrouter import call_openrouter
from mind_lite.llm.prompts import build_ask_prompt


def generate_answer(
    query: str,
    citations: list[dict],
    config: LlmConfig | None = None,
) -> dict[str, Any]:
    if config is None:
        config = get_llm_config()
    
    prompt = build_ask_prompt(query, citations)
    provider = get_provider_for_model(config.active_model)
    
    if provider == "lmstudio" or config.active_provider == "lmstudio":
        result = call_lmstudio(
            prompt=prompt,
            model=config.active_model.replace("lmstudio:", ""),
            base_url=config.lmstudio_url,
        )
    else:
        result = call_openrouter(
            prompt=prompt,
            model=config.active_model,
            api_key=config.openrouter_api_key,
        )
    
    if result.get("success"):
        updated_config = add_to_recently_used(
            config,
            config.active_provider,
            config.active_model,
        )
        save_llm_config(updated_config)
    
    return result


def generate_answer_with_fallback(
    query: str,
    citations: list[dict],
    config: LlmConfig | None = None,
) -> dict[str, Any]:
    if config is None:
        config = get_llm_config()
    
    primary_result = generate_answer(query, citations, config)
    
    if primary_result.get("success"):
        return primary_result
    
    if config.active_provider != "lmstudio" and config.openrouter_api_key:
        fallback_result = call_lmstudio(
            prompt=build_ask_prompt(query, citations),
            base_url=config.lmstudio_url,
        )
        if fallback_result.get("success"):
            fallback_result["fallback_used"] = True
            fallback_result["fallback_reason"] = primary_result.get("error", "primary_failed")
            return fallback_result
    
    return primary_result

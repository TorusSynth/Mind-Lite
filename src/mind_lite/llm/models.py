from typing import Any


MODEL_CATALOG: dict[str, list[dict[str, Any]]] = {
    "free": [
        {"id": "openrouter/free", "name": "Auto (Best Free)", "context": 200000, "provider": "openrouter"},
        {"id": "deepseek/deepseek-r1-0528:free", "name": "DeepSeek R1", "context": 164000, "provider": "openrouter"},
        {"id": "google/gemini-2.0-flash-exp:free", "name": "Gemini 2.0 Flash", "context": 1000000, "provider": "openrouter"},
        {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3 70B", "context": 131000, "provider": "openrouter"},
        {"id": "qwen/qwen3-coder:free", "name": "Qwen3 Coder", "context": 262000, "provider": "openrouter"},
        {"id": "arcee-ai/trinity-large-preview:free", "name": "Trinity Large", "context": 131000, "provider": "openrouter"},
    ],
    "local": [
        {"id": "lmstudio:local", "name": "LM Studio (Local)", "context": 128000, "provider": "lmstudio"},
    ],
    "smart": [
        {"id": "anthropic/claude-opus-4.6", "name": "Claude Opus 4.6", "context": 200000, "provider": "openrouter"},
        {"id": "openai/gpt-5.2", "name": "GPT-5.2", "context": 400000, "provider": "openrouter"},
        {"id": "deepseek/deepseek-v3.2", "name": "DeepSeek V3.2", "context": 164000, "provider": "openrouter"},
        {"id": "google/gemini-3-flash-preview", "name": "Gemini 3 Flash", "context": 1000000, "provider": "openrouter"},
    ],
}


def get_models_by_category(category: str) -> list[dict[str, Any]]:
    return MODEL_CATALOG.get(category, [])


def get_all_models() -> list[dict[str, Any]]:
    all_models = []
    for category, models in MODEL_CATALOG.items():
        for model in models:
            model_with_category = {**model, "category": category}
            all_models.append(model_with_category)
    return all_models


def get_model_by_id(model_id: str) -> dict[str, Any] | None:
    for category, models in MODEL_CATALOG.items():
        for model in models:
            if model["id"] == model_id:
                return {**model, "category": category}
    return None


def get_provider_for_model(model_id: str) -> str:
    model = get_model_by_id(model_id)
    if model:
        return model.get("provider", "openrouter")
    if model_id.startswith("lmstudio:"):
        return "lmstudio"
    return "openrouter"

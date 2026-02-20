import os
from typing import Any

import httpx


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def call_openrouter(
    prompt: str,
    model: str,
    api_key: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 1000,
    timeout: float = 60.0,
    site_url: str = "http://localhost:8000",
    site_name: str = "Mind Lite",
) -> dict[str, Any]:
    key = api_key or os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        return {
            "success": False,
            "error": "No OpenRouter API key configured",
            "content": "",
            "model": model,
            "provider": "openrouter",
        }
    
    try:
        response = httpx.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "HTTP-Referer": site_url,
                "X-Title": site_name,
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {
            "success": True,
            "content": content,
            "model": model,
            "provider": "openrouter",
        }
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            "content": "",
            "model": model,
            "provider": "openrouter",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "content": "",
            "model": model,
            "provider": "openrouter",
        }


def check_openrouter_available(api_key: str | None = None) -> bool:
    key = api_key or os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        return False
    
    try:
        response = httpx.get(
            f"{OPENROUTER_BASE_URL}/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10.0,
        )
        return response.status_code == 200
    except Exception:
        return False

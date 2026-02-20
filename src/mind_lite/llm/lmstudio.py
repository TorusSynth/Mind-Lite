from typing import Any

import httpx


def call_lmstudio(
    prompt: str,
    model: str = "local-model",
    base_url: str = "http://localhost:1234",
    temperature: float = 0.1,
    max_tokens: int = 1000,
    timeout: float = 30.0,
) -> dict[str, Any]:
    try:
        response = httpx.post(
            f"{base_url}/v1/chat/completions",
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
            "provider": "lmstudio",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "content": "",
            "model": model,
            "provider": "lmstudio",
        }


def check_lmstudio_available(base_url: str = "http://localhost:1234") -> bool:
    try:
        response = httpx.get(f"{base_url}/v1/models", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False

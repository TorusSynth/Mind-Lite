import os
import pytest
import httpx


def pytest_collection_modifyitems(config, items):
    skip_integration = os.getenv("SKIP_INTEGRATION", "").lower() in ("1", "true", "yes")
    integration_marker = pytest.mark.skip(reason="SKIP_INTEGRATION is set")
    
    for item in items:
        if "integration" in item.keywords and skip_integration:
            item.add_marker(integration_marker)


@pytest.fixture
def qdrant_available():
    url = os.getenv("MIND_LITE_QDRANT_URL", "http://localhost:6333")
    try:
        response = httpx.get(f"{url}/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def lmstudio_available():
    url = os.getenv("MIND_LITE_LMSTUDIO_URL", "http://localhost:1234")
    try:
        response = httpx.get(f"{url}/v1/models", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def openrouter_available():
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return False
    try:
        response = httpx.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def skip_if_no_qdrant(qdrant_available):
    if not qdrant_available:
        pytest.skip("Qdrant not available at localhost:6333")


@pytest.fixture
def skip_if_no_lmstudio(lmstudio_available):
    if not lmstudio_available:
        pytest.skip("LM Studio not available at localhost:1234")


@pytest.fixture
def skip_if_no_openrouter(openrouter_available):
    if not openrouter_available:
        pytest.skip("OpenRouter API key not configured or invalid")


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_rag.db")


@pytest.fixture
def temp_qdrant_collection(qdrant_available):
    if not qdrant_available:
        pytest.skip("Qdrant not available")
    
    from qdrant_client import QdrantClient
    from mind_lite.rag.config import get_rag_config
    
    config = get_rag_config()
    client = QdrantClient(url=config.qdrant_url)
    
    test_collection = f"test_{config.collection_name}"
    
    yield client, test_collection
    
    try:
        client.delete_collection(test_collection)
    except Exception:
        pass

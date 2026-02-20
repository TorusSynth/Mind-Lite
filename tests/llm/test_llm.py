import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class LlmConfigTests(unittest.TestCase):
    def test_default_config_values(self):
        from mind_lite.llm.config import LlmConfig

        config = LlmConfig()
        self.assertEqual(config.active_provider, "lmstudio")
        self.assertEqual(config.active_model, "lmstudio:local")
        self.assertEqual(config.openrouter_api_key, "")
        self.assertEqual(config.lmstudio_url, "http://localhost:1234")
        self.assertEqual(config.recently_used, [])

    def test_config_to_dict_and_from_dict(self):
        from mind_lite.llm.config import LlmConfig

        original = LlmConfig(
            active_provider="openrouter",
            active_model="deepseek/deepseek-r1-0528:free",
            openrouter_api_key="test-key",
            lmstudio_url="http://localhost:9999",
            recently_used=[{"provider": "lmstudio", "model": "lmstudio:local"}],
        )

        data = original.to_dict()
        restored = LlmConfig.from_dict(data)

        self.assertEqual(restored.active_provider, "openrouter")
        self.assertEqual(restored.active_model, "deepseek/deepseek-r1-0528:free")
        self.assertEqual(restored.openrouter_api_key, "test-key")
        self.assertEqual(restored.lmstudio_url, "http://localhost:9999")
        self.assertEqual(len(restored.recently_used), 1)

    def test_add_to_recently_used_limits_to_five(self):
        from mind_lite.llm.config import LlmConfig, add_to_recently_used

        config = LlmConfig(recently_used=[
            {"provider": "p1", "model": "m1"},
            {"provider": "p2", "model": "m2"},
            {"provider": "p3", "model": "m3"},
            {"provider": "p4", "model": "m4"},
            {"provider": "p5", "model": "m5"},
        ])

        updated = add_to_recently_used(config, "p6", "m6")
        self.assertEqual(len(updated.recently_used), 5)
        self.assertEqual(updated.recently_used[0], {"provider": "p6", "model": "m6"})

    def test_add_to_recently_used_moves_existing_to_front(self):
        from mind_lite.llm.config import LlmConfig, add_to_recently_used

        config = LlmConfig(recently_used=[
            {"provider": "p1", "model": "m1"},
            {"provider": "p2", "model": "m2"},
        ])

        updated = add_to_recently_used(config, "p1", "m1")
        self.assertEqual(len(updated.recently_used), 2)
        self.assertEqual(updated.recently_used[0], {"provider": "p1", "model": "m1"})

    def test_get_llm_config_reads_env_vars(self):
        from mind_lite.llm.config import get_llm_config

        with patch.dict(os.environ, {
            "OPENROUTER_API_KEY": "env-key",
            "MIND_LITE_LMSTUDIO_URL": "http://custom:5678",
        }):
            config = get_llm_config()
            self.assertEqual(config.openrouter_api_key, "env-key")
            self.assertEqual(config.lmstudio_url, "http://custom:5678")


class LlmModelsTests(unittest.TestCase):
    def test_model_catalog_has_required_categories(self):
        from mind_lite.llm.models import MODEL_CATALOG

        self.assertIn("free", MODEL_CATALOG)
        self.assertIn("local", MODEL_CATALOG)
        self.assertIn("smart", MODEL_CATALOG)

    def test_get_models_by_category(self):
        from mind_lite.llm.models import get_models_by_category

        free_models = get_models_by_category("free")
        self.assertGreater(len(free_models), 0)

        local_models = get_models_by_category("local")
        self.assertGreater(len(local_models), 0)

    def test_get_all_models(self):
        from mind_lite.llm.models import get_all_models

        all_models = get_all_models()
        self.assertGreater(len(all_models), 0)

        for model in all_models:
            self.assertIn("category", model)
            self.assertIn("id", model)
            self.assertIn("name", model)
            self.assertIn("provider", model)

    def test_get_model_by_id(self):
        from mind_lite.llm.models import get_model_by_id

        model = get_model_by_id("lmstudio:local")
        self.assertIsNotNone(model)
        self.assertEqual(model["category"], "local")

    def test_get_provider_for_model(self):
        from mind_lite.llm.models import get_provider_for_model

        self.assertEqual(get_provider_for_model("lmstudio:local"), "lmstudio")
        self.assertEqual(get_provider_for_model("deepseek/deepseek-r1-0528:free"), "openrouter")


class LlmPromptsTests(unittest.TestCase):
    def test_build_ask_prompt_with_citations(self):
        from mind_lite.llm.prompts import build_ask_prompt

        citations = [
            {"note_id": "notes/test.md", "excerpt": "This is test content."},
        ]
        prompt = build_ask_prompt("What is this?", citations)

        self.assertIn("What is this?", prompt)
        self.assertIn("notes/test.md", prompt)
        self.assertIn("This is test content.", prompt)

    def test_build_ask_prompt_without_citations(self):
        from mind_lite.llm.prompts import build_ask_prompt

        prompt = build_ask_prompt("What is this?", [])

        self.assertIn("No relevant notes found", prompt)
        self.assertIn("What is this?", prompt)

    def test_build_ask_prompt_limits_citations(self):
        from mind_lite.llm.prompts import build_ask_prompt

        citations = [
            {"note_id": f"notes/{i}.md", "excerpt": f"Content {i}"}
            for i in range(10)
        ]
        prompt = build_ask_prompt("Question", citations)

        self.assertIn("notes/0.md", prompt)
        self.assertIn("notes/4.md", prompt)
        self.assertNotIn("notes/5.md", prompt)


if __name__ == "__main__":
    unittest.main()

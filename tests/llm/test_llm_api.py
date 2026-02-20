import unittest
from unittest.mock import MagicMock, patch


class LlmApiTests(unittest.TestCase):
    def test_llm_list_models_returns_catalog(self):
        from mind_lite.api.service import ApiService

        service = ApiService()
        result = service.llm_list_models()

        self.assertIn("models", result)
        self.assertIn("free", result["models"])
        self.assertIn("local", result["models"])
        self.assertIn("smart", result["models"])

    def test_llm_get_config_returns_current_config(self):
        from mind_lite.api.service import ApiService

        service = ApiService()
        result = service.llm_get_config()

        self.assertIn("active_provider", result)
        self.assertIn("active_model", result)
        self.assertIn("has_openrouter_key", result)
        self.assertIn("lmstudio_url", result)
        self.assertIn("recently_used", result)

    def test_llm_set_config_validates_provider(self):
        from mind_lite.api.service import ApiService

        service = ApiService()
        
        with self.assertRaises(ValueError) as ctx:
            service.llm_set_config({"provider": "invalid", "model": "test"})
        
        self.assertIn("provider must be", str(ctx.exception))

    def test_llm_set_config_validates_model(self):
        from mind_lite.api.service import ApiService

        service = ApiService()
        
        with self.assertRaises(ValueError) as ctx:
            service.llm_set_config({"provider": "lmstudio", "model": ""})
        
        self.assertIn("model is required", str(ctx.exception))

    def test_llm_set_config_saves_config(self):
        from mind_lite.api.service import ApiService

        service = ApiService()
        result = service.llm_set_config({
            "provider": "openrouter",
            "model": "deepseek/deepseek-r1-0528:free",
        })

        self.assertEqual(result["active_provider"], "openrouter")
        self.assertEqual(result["active_model"], "deepseek/deepseek-r1-0528:free")

    def test_llm_set_api_key_validates_input(self):
        from mind_lite.api.service import ApiService

        service = ApiService()
        
        with self.assertRaises(ValueError) as ctx:
            service.llm_set_api_key({"api_key": 123})
        
        self.assertIn("api_key must be a string", str(ctx.exception))

    def test_llm_set_api_key_saves_key(self):
        from mind_lite.api.service import ApiService

        service = ApiService()
        result = service.llm_set_api_key({"api_key": "test-key-123"})

        self.assertEqual(result["status"], "saved")
        self.assertTrue(result["has_key"])

    def test_llm_clear_api_key(self):
        from mind_lite.api.service import ApiService

        service = ApiService()
        service.llm_set_api_key({"api_key": "test-key"})
        result = service.llm_clear_api_key()

        self.assertEqual(result["status"], "cleared")


class LlmGenerateTests(unittest.TestCase):
    def test_generate_answer_calls_correct_provider(self):
        from mind_lite.llm.generate import generate_answer
        from mind_lite.llm.config import LlmConfig

        config = LlmConfig(
            active_provider="lmstudio",
            active_model="lmstudio:local",
            lmstudio_url="http://localhost:1234",
        )

        with patch("mind_lite.llm.generate.call_lmstudio") as mock_lm:
            mock_lm.return_value = {"success": True, "content": "Test answer"}
            result = generate_answer("Test query", [], config)

            mock_lm.assert_called_once()
            self.assertTrue(result["success"])
            self.assertEqual(result["content"], "Test answer")

    def test_generate_answer_calls_openrouter_for_cloud_models(self):
        from mind_lite.llm.generate import generate_answer
        from mind_lite.llm.config import LlmConfig

        config = LlmConfig(
            active_provider="openrouter",
            active_model="deepseek/deepseek-r1-0528:free",
            openrouter_api_key="test-key",
        )

        with patch("mind_lite.llm.generate.call_openrouter") as mock_or:
            mock_or.return_value = {"success": True, "content": "Cloud answer"}
            result = generate_answer("Test query", [], config)

            mock_or.assert_called_once()
            self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()

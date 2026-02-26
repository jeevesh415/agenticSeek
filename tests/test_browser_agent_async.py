import unittest
import asyncio
import os
from unittest.mock import MagicMock, patch, AsyncMock
import sys

sys.path.append(os.getcwd())

class TestBrowserAgentAsync(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # Setup mocks for all dependencies
        cls.modules_patcher = patch.dict(sys.modules, {
            'torch': MagicMock(),
            'transformers': MagicMock(),
            'selenium': MagicMock(),
            'selenium.webdriver': MagicMock(),
            'selenium.webdriver.chrome': MagicMock(),
            'selenium.webdriver.chrome.service': MagicMock(),
            'selenium.webdriver.chrome.options': MagicMock(),
            'selenium.webdriver.common': MagicMock(),
            'selenium.webdriver.common.by': MagicMock(),
            'selenium.webdriver.support': MagicMock(),
            'selenium.webdriver.support.ui': MagicMock(),
            'selenium.webdriver.support.expected_conditions': MagicMock(),
            'selenium.common': MagicMock(),
            'selenium.common.exceptions': MagicMock(),
            'selenium.webdriver.common.action_chains': MagicMock(),
            'bs4': MagicMock(),
            'markdownify': MagicMock(),
            'fake_useragent': MagicMock(),
            'selenium_stealth': MagicMock(),
            'undetected_chromedriver': MagicMock(),
            'chromedriver_autoinstaller': MagicMock(),
            'colorama': MagicMock(),
            'termcolor': MagicMock(),
            'pydantic': MagicMock(),
            'openai': MagicMock(),
            'ollama': MagicMock(),
            'groq': MagicMock(),
            'httpx': MagicMock(),
            'numpy': MagicMock(),
            'librosa': MagicMock(),
            'pyaudio': MagicMock(),
            'requests': MagicMock(),
            'dotenv': MagicMock(),
            'h2': MagicMock(),
            'certifi': MagicMock(),
            'sources.tools.searxSearch': MagicMock()
        })
        cls.modules_patcher.start()

        # Patch utility functions to avoid import errors or side effects during import
        cls.utility_patcher_1 = patch('sources.utility.pretty_print')
        cls.utility_patcher_2 = patch('sources.utility.animate_thinking')
        cls.utility_patcher_1.start()
        cls.utility_patcher_2.start()

        # Import inside setup after patching modules
        global BrowserAgent
        from sources.agents.browser_agent import BrowserAgent

    @classmethod
    def tearDownClass(cls):
        cls.utility_patcher_1.stop()
        cls.utility_patcher_2.stop()
        cls.modules_patcher.stop()

    def setUp(self):
        self.browser_mock = MagicMock()
        # Mock load_prompt to return a dummy string
        with patch.object(BrowserAgent, 'load_prompt', return_value="dummy prompt"):
            mock_provider = MagicMock()
            mock_provider.get_model_name.return_value = "mock_model"
            # Mock Memory constructor since it's called in __init__
            with patch('sources.agents.browser_agent.Memory') as MockMemory, \
                 patch('sources.agents.browser_agent.searxSearch') as MockSearx, \
                 patch('sources.agents.browser_agent.Logger') as MockLogger:
                self.agent = BrowserAgent("TestAgent", "dummy_path", mock_provider, browser=self.browser_mock)
                self.agent.memory = MagicMock() # Ensure memory is mocked on instance
                self.agent.memory.trim_text_to_max_ctx.side_effect = lambda x: x

    async def test_get_page_text_is_async(self):
        # Verify get_page_text is async
        self.assertTrue(asyncio.iscoroutinefunction(self.agent.get_page_text))

    async def test_get_page_text_calls_browser_async(self):
        # Verify it calls browser.get_text via run_in_executor
        self.browser_mock.get_text.return_value = "Page Content"
        result = await self.agent.get_page_text(limit_to_model_ctx=False)
        self.assertEqual(result, "Page Content")
        # Verify browser.get_text was called
        self.browser_mock.get_text.assert_called()

    async def test_run_browser_cmd(self):
        # Verify _run_browser_cmd works
        def dummy_func(arg):
            return f"processed {arg}"

        result = await self.agent._run_browser_cmd(dummy_func, "test")
        self.assertEqual(result, "processed test")

if __name__ == '__main__':
    unittest.main()

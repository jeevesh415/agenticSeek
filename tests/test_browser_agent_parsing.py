import unittest
import os
import sys
from unittest.mock import MagicMock

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock 3rd party dependencies
sys.modules["torch"] = MagicMock()
sys.modules["transformers"] = MagicMock()
sys.modules["pyaudio"] = MagicMock()
sys.modules["librosa"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["scipy"] = MagicMock()
sys.modules["selenium"] = MagicMock()
sys.modules["selenium.webdriver"] = MagicMock()
sys.modules["selenium.webdriver.chrome.options"] = MagicMock()
sys.modules["selenium.webdriver.chrome.service"] = MagicMock()
sys.modules["selenium.webdriver.common.by"] = MagicMock()
sys.modules["selenium.webdriver.support.ui"] = MagicMock()
sys.modules["selenium.webdriver.support"] = MagicMock()
sys.modules["selenium.common.exceptions"] = MagicMock()
sys.modules["selenium.webdriver.common.action_chains"] = MagicMock()
sys.modules["bs4"] = MagicMock()
sys.modules["markdownify"] = MagicMock()
sys.modules["fake_useragent"] = MagicMock()
sys.modules["selenium_stealth"] = MagicMock()
sys.modules["undetected_chromedriver"] = MagicMock()
sys.modules["chromedriver_autoinstaller"] = MagicMock()
sys.modules["certifi"] = MagicMock()
# sys.modules["ssl"] = MagicMock() # Removed because it breaks requests/urllib3
sys.modules["httpx"] = MagicMock()
sys.modules["dotenv"] = MagicMock()

# Do NOT mock sources modules here, so other tests can use them correctly.
# If BrowserAgent needs them, it will import the real ones (which use the mocked 3rd party libs above)

from sources.agents.browser_agent import BrowserAgent

class TestBrowserAgentParsing(unittest.TestCase):
    def setUp(self):
        # Set environment variable required by searxSearch
        os.environ["SEARXNG_BASE_URL"] = "http://localhost:8080"

        # Initialize a basic BrowserAgent instance for testing
        provider_mock = MagicMock()
        provider_mock.get_model_name.return_value = "test-model"

        # BrowserAgent creates Browser and searxSearch instances.
        # Since we mocked their dependencies, they should instantiate but might fail if they do complex logic in __init__
        # Browser __init__ takes a driver.

        # We need to mock Browser class if we pass it to BrowserAgent
        browser_mock = MagicMock()

        self.agent = BrowserAgent(
            name="TestAgent",
            prompt_path="prompts/base/browser_agent.txt",
            provider=provider_mock,
            browser=browser_mock
        )

    def test_extract_links(self):
        # Test various link formats
        test_text = """
        Check this out: https://thriveonai.com/15-ai-startups-in-japan-to-take-note-of, and www.google.com!
        Also try https://test.org/about?page=1, hey this one as well bro https://weatherstack.com/documentation/.
        """
        expected = [
            "https://thriveonai.com/15-ai-startups-in-japan-to-take-note-of",
            "www.google.com",
            "https://test.org/about?page=1",
            "https://weatherstack.com/documentation"
        ]
        result = self.agent.extract_links(test_text)
        self.assertEqual(result, expected)

    def test_extract_form(self):
        # Test form extraction
        test_text = """
        Fill this: [username](john) and [password](secret123)
        Not a form: [random]text
        """
        expected = ["[username](john)", "[password](secret123)"]
        result = self.agent.extract_form(test_text)
        self.assertEqual(result, expected)

    def test_clean_links(self):
        # Test link cleaning
        test_links = [
            "https://example.com.",
            "www.test.com,",
            "https://clean.org!",
            "https://good.com"
        ]
        expected = [
            "https://example.com",
            "www.test.com",
            "https://clean.org",
            "https://good.com"
        ]
        result = self.agent.clean_links(test_links)
        self.assertEqual(result, expected)

    def test_parse_answer(self):
        # Test parsing answer with notes and links
        test_text = """
        Here's some info
        Note: This is important. We are doing test it's very cool.
        action: 
        i wanna navigate to https://test.com
        """
        self.agent.parse_answer(test_text)
        self.assertEqual(self.agent.notes[0], "Note: This is important. We are doing test it's very cool.")

if __name__ == "__main__":
    unittest.main()
import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # Add project root to Python path
from sources.tools.searxSearch import searxSearch
from dotenv import load_dotenv
import requests  # Import the requests module
from unittest.mock import patch, MagicMock

load_dotenv()

class TestSearxSearch(unittest.TestCase):

    def setUp(self):
        os.environ['SEARXNG_BASE_URL'] = "http://127.0.0.1:8080"  # Set the environment variable
        self.base_url = os.getenv("SEARXNG_BASE_URL")
        self.search_tool = searxSearch(base_url=self.base_url)
        self.valid_query = "test query"
        self.invalid_query = ""

    def test_initialization_with_env_variable(self):
        # Ensure the tool initializes correctly with the base URL from the environment variable
        os.environ['SEARXNG_BASE_URL'] = "http://test.example.com"
        search_tool = searxSearch()
        self.assertEqual(search_tool.base_url, "http://test.example.com")
        del os.environ['SEARXNG_BASE_URL']

    def test_initialization_no_base_url(self):
        # Ensure the tool raises an error if no base URL is provided
        # Remove the environment variable to ensure the ValueError is raised
        if 'SEARXNG_BASE_URL' in os.environ:
            del os.environ['SEARXNG_BASE_URL']
        with self.assertRaises(ValueError):
            searxSearch(base_url=None)
        # Restore the environment variable after the test
        os.environ['SEARXNG_BASE_URL'] = "http://searx.lan"

    def test_execute_valid_query(self):
        # Execute the search and verify the result
        result = self.search_tool.execute([self.valid_query])
        print(f"Output from test_execute_valid_query: {result}")
        self.assertTrue(isinstance(result, str), "Result should be a string.")
        self.assertNotEqual(result, "", "Result should not be empty. Check SearxNG instance.")

    def test_execute_empty_query(self):
        # Test with an empty query
        result = self.search_tool.execute([""])
        print(f"Output from test_execute_empty_query: {result}")
        self.assertEqual(result, "Error: Empty search query provided.")

    def test_execute_no_query(self):
        # Test with no query provided
        result = self.search_tool.execute([])
        print(f"Output from test_execute_no_query: {result}")
        self.assertEqual(result, "Error: No search query provided.")

    def test_execute_request_exception(self):
        # Test a request exception by temporarily modifying the base_url to an invalid one
        original_base_url = self.search_tool.base_url
        self.search_tool.base_url = "http://invalid_url"
        try:
            result = self.search_tool.execute([self.valid_query])
            print(f"Output from test_execute_request_exception: {result}")
            self.assertTrue("Error during search" in result)
        finally:
            self.search_tool.base_url = original_base_url  # Restore the original base_url

    def test_execute_no_results(self):
        # Execute the search and verify that an empty string is handled correctly
        result = self.search_tool.execute(["nonexistent query that should return no results"])
        print(f"Output from test_execute_no_results: {result}")
        self.assertTrue(isinstance(result, str), "Result should be a string.")
        # Allow empty results, but print a warning
        if result == "":
            print("Warning: SearxNG returned no results for a query that should have returned no results.")

    def test_execution_failure_check_error(self):
        # Test when the output contains an error
        output = "Error: Something went wrong"
        self.assertTrue(self.search_tool.execution_failure_check(output))

    def test_execution_failure_check_no_error(self):
        # Test when the output does not contain an error
        output = "Search completed successfully"
        self.assertFalse(self.search_tool.execution_failure_check(output))

    def test_link_valid(self):
        # Test 1: Invalid URL
        result = self.search_tool.link_valid("ftp://example.com")
        self.assertEqual(result, "Status: Invalid URL")

        # Test 2: OK URL (Mocked)
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "text/html"}
            mock_response.iter_content.return_value = [b"This is a normal page."]

            mock_get.return_value.__enter__.return_value = mock_response
            mock_get.return_value.__exit__.return_value = None

            result = self.search_tool.link_valid("http://example.com")
            self.assertEqual(result, "Status: OK")

        # Test 3: Paywall URL (Mocked)
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "text/html"}
            mock_response.iter_content.return_value = [b"Sorry, Member-only content."]

            mock_get.return_value.__enter__.return_value = mock_response
            mock_get.return_value.__exit__.return_value = None

            result = self.search_tool.link_valid("http://paywall.com")
            self.assertEqual(result, "Status: Possible Paywall")

        # Test 4: 404 URL (Mocked)
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404

            mock_get.return_value.__enter__.return_value = mock_response
            mock_get.return_value.__exit__.return_value = None

            result = self.search_tool.link_valid("http://example.com/404")
            self.assertEqual(result, "Status: 404 Not Found")

        # Test 5: Non-text content (Image)
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "image/png"}
            mock_response.iter_content.return_value = [b"binary data"]

            mock_get.return_value.__enter__.return_value = mock_response
            mock_get.return_value.__exit__.return_value = None

            result = self.search_tool.link_valid("http://example.com/image.png")
            self.assertEqual(result, "Status: OK")
            mock_response.iter_content.assert_not_called()

if __name__ == '__main__':
    unittest.main()

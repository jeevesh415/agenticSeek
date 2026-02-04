import unittest
import unittest.mock
import os
import sys
import asyncio
import httpx
from unittest import IsolatedAsyncioTestCase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # Add project root to Python path
from sources.tools.searxSearch import searxSearch
from dotenv import load_dotenv

load_dotenv()

class TestSearxSearch(IsolatedAsyncioTestCase):

    def setUp(self):
        os.environ['WORK_DIR'] = "/tmp"  # Ensure WORK_DIR is set for Tools init
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

    async def test_execute_valid_query(self):
        # Mocking the httpx response
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html><body>
        <article class="result">
            <a class="url_header" href="http://example.com"></a>
            <h3>Example Title</h3>
            <p class="content">Example Snippet</p>
        </article>
        </body></html>
        """
        mock_response.raise_for_status = unittest.mock.Mock()

        # Setup mocking context
        # Patching httpx.AsyncClient.post to return the mock_response
        with unittest.mock.patch("httpx.AsyncClient.post", new_callable=unittest.mock.AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await self.search_tool.execute([self.valid_query])
            print(f"Output from test_execute_valid_query: {result}")
            self.assertTrue(isinstance(result, str), "Result should be a string.")
            self.assertIn("Example Title", result)
            self.assertIn("http://example.com", result)

    async def test_execute_empty_query(self):
        # Test with an empty query
        result = await self.search_tool.execute([""])
        print(f"Output from test_execute_empty_query: {result}")
        self.assertEqual(result, "Error: Empty search query provided.")

    async def test_execute_no_query(self):
        # Test with no query provided
        result = await self.search_tool.execute([])
        print(f"Output from test_execute_no_query: {result}")
        self.assertEqual(result, "Error: No search query provided.")

    async def test_execute_request_exception(self):
        # Test a request exception
        with unittest.mock.patch("httpx.AsyncClient.post", new_callable=unittest.mock.AsyncMock) as mock_post:
            # We need to simulate an exception. httpx.RequestError requires a request argument
            request = httpx.Request("POST", "http://test")
            mock_post.side_effect = httpx.RequestError("Mock Error", request=request)

            try:
                result = await self.search_tool.execute([self.valid_query])
                self.fail("Should have raised Exception")
            except Exception as e:
                print(f"Output from test_execute_request_exception: {e}")
                self.assertTrue("Searxng search failed" in str(e))

    async def test_execute_no_results(self):
        # Execute the search and verify that an empty string is handled correctly
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = unittest.mock.Mock()

        with unittest.mock.patch("httpx.AsyncClient.post", new_callable=unittest.mock.AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await self.search_tool.execute(["nonexistent query that should return no results"])
            print(f"Output from test_execute_no_results: {result}")
            self.assertEqual(result, "No search results, web search failed.")

    def test_execution_failure_check_error(self):
        # Test when the output contains an error
        output = "Error: Something went wrong"
        self.assertTrue(self.search_tool.execution_failure_check(output))

    def test_execution_failure_check_no_error(self):
        # Test when the output does not contain an error
        output = "Search completed successfully"
        self.assertFalse(self.search_tool.execution_failure_check(output))

if __name__ == '__main__':
    unittest.main()

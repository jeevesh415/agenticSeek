
import asyncio
import unittest
import time
import sys
import os
from unittest.mock import MagicMock, patch

# Add sources to path
sys.path.append(os.getcwd())

from sources.tools.webSearch import webSearch

class TestWebSearchAsync(unittest.IsolatedAsyncioTestCase):
    async def test_execute_non_blocking(self):
        """
        Verify that webSearch.execute is non-blocking and allows other async tasks to run.
        """
        # Set up a fake environment variable for WORK_DIR if needed (though webSearch doesn't strictly need it if config is mocked or not used)
        # But Tools base class needs it.
        # We assume os.environ is patched or .env exists (which I created).
        # To be safe, let's patch os.getenv or rely on the environment setup.

        tool = webSearch(api_key="fake")

        counter = 0
        async def background_task():
            nonlocal counter
            while True:
                counter += 1
                await asyncio.sleep(0.01)

        # Mock httpx
        mock_client = MagicMock()

        async def mock_get(url, *args, **kwargs):
            # Simulate network delay
            await asyncio.sleep(0.1)
            mock_resp = MagicMock()
            mock_resp.status_code = 200

            if "serpapi.com" in url:
                mock_resp.json.return_value = {
                    "organic_results": [{"link": f"http://example.com/{i}"} for i in range(5)]
                }
            else:
                mock_resp.text = "ok"

            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        mock_client.get.side_effect = mock_get
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch('httpx.AsyncClient', return_value=mock_client):
            bg = asyncio.create_task(background_task())

            start = time.time()
            result = await tool.execute(["test"])
            end = time.time()

            bg.cancel()
            try:
                await bg
            except asyncio.CancelledError:
                pass

            # Verify execution time is roughly 0.2s (search + links)
            # and ticks > 0
            self.assertGreater(counter, 0, "Background task should have run during execute")
            self.assertTrue("Title:No title" in result, "Result should contain search results")

if __name__ == '__main__':
    unittest.main()

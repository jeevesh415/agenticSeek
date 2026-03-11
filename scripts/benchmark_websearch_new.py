import time
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sources.tools.webSearch import webSearch

PORT = 8081

class MockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Simulate SerpAPI Search
        if "/search" in self.path:
            time.sleep(0.1) # Simulating network latency
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            mock_data = {
                "organic_results": [
                    {"title": f"Title {i}", "snippet": f"Snippet {i}", "link": f"http://localhost:{PORT}/link{i}"}
                    for i in range(10)
                ]
            }
            self.wfile.write(json.dumps(mock_data).encode())

        # Simulate linked pages
        elif "/link" in self.path:
            time.sleep(0.05) # Simulating network latency
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body>test content ok</body></html>")

def run_server():
    server = HTTPServer(('localhost', PORT), MockHandler)
    server.serve_forever()

def run_benchmark(num_runs=3):
    # Start server in background
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1) # wait for server to start

    # We patch the hardcoded url inside fetch_search_results logic
    # instead of httpx.AsyncClient.get, since our previous mock broke it
    original_execute = webSearch.execute

    def wrapped_execute(self, blocks, safety=True):
        import httpx
        original_get = httpx.AsyncClient.get

        async def side_effect(client_self, url, **kwargs):
            if "serpapi.com" in url:
                url = f"http://localhost:{PORT}/search"
            return await original_get(client_self, url, **kwargs)

        with patch('httpx.AsyncClient.get', new=side_effect):
            return original_execute(self, blocks, safety)

    webSearch.execute = wrapped_execute

    tool = webSearch(api_key="mock_key")

    # redirect print to avoid clutter
    import io
    sys.stdout = io.StringIO()

    start_time = time.perf_counter()
    for _ in range(num_runs):
        tool.execute(["test query"])
    end_time = time.perf_counter()

    # restore stdout
    sys.stdout = sys.__stdout__

    avg_time = (end_time - start_time) / num_runs
    print(f"Benchmark completed. Average execution time over {num_runs} runs: {avg_time:.4f} seconds.")
    return avg_time

if __name__ == "__main__":
    run_benchmark(5)

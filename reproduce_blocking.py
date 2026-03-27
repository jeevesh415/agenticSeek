
import sys
import asyncio
import time
from unittest.mock import MagicMock

# Helper to mock modules recursively
def mock_module(module_name):
    m = MagicMock()
    m.__path__ = [] # Mark as package
    sys.modules[module_name] = m

# List of modules to mock
modules = [
    "torch", "transformers", "librosa", "numpy", "pyaudio", "colorama", "termcolor",
    "h2", "httpx", "markdownify", "bs4", "dotenv", "requests", "ollama", "openai",
    "configparser", "pydantic", "jieba", "cn2an", "pyppeteer", "playwright",
    "playwright.sync_api", "googlesearch", "PIL",
    "selenium",
    "selenium.webdriver",
    "selenium.webdriver.chrome",
    "selenium.webdriver.chrome.service",
    "selenium.webdriver.chrome.options",
    "selenium.webdriver.common",
    "selenium.webdriver.common.by",
    "selenium.webdriver.common.keys",
    "selenium.webdriver.common.action_chains",
    "selenium.webdriver.support",
    "selenium.webdriver.support.ui",
    "selenium.webdriver.support.expected_conditions",
    "selenium.common",
    "selenium.common.exceptions",
    "selenium.webdriver.remote",
    "selenium.webdriver.remote.webdriver",
    "selenium.webdriver.remote.webelement",
    "selenium.webdriver.remote.command",
    "webdriver_manager",
    "webdriver_manager.chrome",
    "webdriver_manager.core",
    "webdriver_manager.core.utils",
    "fake_useragent",
    "selenium_stealth",
    "undetected_chromedriver",
    "chromedriver_autoinstaller",
    "certifi",
    "ssl"
]

for m in modules:
    mock_module(m)

# Mock utility functions
sys.modules["sources.utility"] = MagicMock()

# Now import
try:
    from sources.agents.code_agent import CoderAgent
    from sources.agents.agent import Agent
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

# Define the mock execute function
def blocking_execute_modules(self, answer):
    print(f"[{time.time():.3f}] Starting blocking execute_modules...")
    time.sleep(2.0)
    print(f"[{time.time():.3f}] Finished blocking execute_modules.")
    self.stop = True # Ensure loop breaks
    return True, "Mock feedback"

# Patch CoderAgent methods to avoid initializing real tools/memory
import concurrent.futures

def mock_init(self, name="code_agent", prompt_path="prompt.txt", provider=None, verbose=False):
    self.stop = False
    self.memory = MagicMock()
    self.logger = MagicMock()
    self.status_message = "Ready"
    self.last_answer = None
    self.last_reasoning = None
    self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    self.agent_name = name
    self.type = "code_agent"
    self.role = "code"
    self.blocks_result = []

CoderAgent.__init__ = mock_init

async def mock_llm_request(self):
    print(f"[{time.time():.3f}] LLM Request called")
    return "```python\nprint('hello')\n```", "reasoning"

async def mock_wait_message(self, sm):
    pass

CoderAgent.llm_request = mock_llm_request
CoderAgent.wait_message = mock_wait_message
CoderAgent.add_sys_info_prompt = lambda self, p: p
CoderAgent.show_answer = lambda self: None
CoderAgent.remove_blocks = lambda self, a: a
CoderAgent.get_last_tool_type = lambda self: "python"
CoderAgent.execute_modules = blocking_execute_modules

# Create instance
agent = CoderAgent()

async def run_reproduction():
    print("Starting reproduction...")

    # Background task to show heartbeat
    async def heartbeat():
        start_time = time.time()
        while time.time() - start_time < 5:
            print(f"[{time.time():.3f}] Heartbeat")
            await asyncio.sleep(0.5)

    heartbeat_task = asyncio.create_task(heartbeat())

    # Run agent process
    print(f"[{time.time():.3f}] Calling process...")
    try:
        await agent.process("test prompt", None)
    except Exception as e:
        print(f"Process failed: {e}")
        import traceback
        traceback.print_exc()

    print(f"[{time.time():.3f}] Process returned.")
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    asyncio.run(run_reproduction())

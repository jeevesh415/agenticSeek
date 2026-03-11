import unittest
import os
import json
import shutil
import sys
from pathlib import Path

# Setup path so we can import cache
sys.path.append(os.path.abspath('llm_server'))
from sources.cache import Cache

class TestCache(unittest.TestCase):
    def setUp(self):
        self.cache_dir = '.test_cache_dir'
        self.cache_file = 'messages.json'
        self.full_path = Path(self.cache_dir) / self.cache_file
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)

    def test_init_creates_file(self):
        c = Cache(cache_dir=self.cache_dir, cache_file=self.cache_file)
        self.assertTrue(os.path.exists(self.full_path))
        with open(self.full_path, 'r') as f:
            data = json.load(f)
        self.assertEqual(data, {})

    def test_backward_compatibility_list_to_dict(self):
        # Create old format file
        old_format_data = [
            {"user": "hello", "assistant": "hi"},
            {"user": "how are you", "assistant": "good"}
        ]
        with open(self.full_path, 'w') as f:
            json.dump(old_format_data, f)

        # Initialize cache, which should convert list to dict internally
        c = Cache(cache_dir=self.cache_dir, cache_file=self.cache_file)

        self.assertTrue(c.is_cached("hello"))
        self.assertEqual(c.get_cached_response("hello"), "hi")
        self.assertTrue(c.is_cached("how are you"))
        self.assertEqual(c.get_cached_response("how are you"), "good")
        self.assertFalse(c.is_cached("nonexistent"))

    def test_add_and_get(self):
        c = Cache(cache_dir=self.cache_dir, cache_file=self.cache_file)
        self.assertFalse(c.is_cached("test_user_msg"))
        self.assertIsNone(c.get_cached_response("test_user_msg"))

        c.add_message_pair("test_user_msg", "test_assistant_msg")

        self.assertTrue(c.is_cached("test_user_msg"))
        self.assertEqual(c.get_cached_response("test_user_msg"), "test_assistant_msg")

    def test_save_and_load(self):
        c1 = Cache(cache_dir=self.cache_dir, cache_file=self.cache_file)
        c1.add_message_pair("msg1", "resp1")
        c1.add_message_pair("msg2", "resp2")

        c2 = Cache(cache_dir=self.cache_dir, cache_file=self.cache_file)
        self.assertTrue(c2.is_cached("msg1"))
        self.assertEqual(c2.get_cached_response("msg2"), "resp2")

        # Check saved format
        with open(self.full_path, 'r') as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)
        self.assertEqual(data["msg1"], "resp1")

if __name__ == '__main__':
    unittest.main()

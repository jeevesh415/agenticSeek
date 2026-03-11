import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Mock dependencies that are not installed
sys.modules['kokoro'] = MagicMock()
sys.modules['IPython'] = MagicMock()
sys.modules['IPython.display'] = MagicMock()
sys.modules['soundfile'] = MagicMock()
sys.modules['colorama'] = MagicMock()
sys.modules['termcolor'] = MagicMock()

# Mock cn2an and jieba to test both cases
sys.modules['cn2an'] = MagicMock()
sys.modules['jieba'] = MagicMock()

from sources.text_to_speech import Speech, CHINESE_IMPORT_FOUND

class TestSpeech(unittest.TestCase):
    def setUp(self):
        # We need to ensure Speech is initialized without actually trying to load kokoro models
        # since we mocked kokoro above, it should be fine.
        pass

    @patch('sources.text_to_speech.pretty_print')
    def test_init_en(self, mock_print):
        speech = Speech(enable=False, language="en")
        self.assertEqual(speech.language, "en")
        mock_print.assert_not_called()

    @patch('sources.text_to_speech.pretty_print')
    def test_init_zh_with_imports(self, mock_print):
        with patch('sources.text_to_speech.CHINESE_IMPORT_FOUND', True):
            speech = Speech(enable=False, language="zh")
            self.assertEqual(speech.language, "zh")
            mock_print.assert_not_called()

    @patch('sources.text_to_speech.pretty_print')
    def test_init_zh_without_imports(self, mock_print):
        with patch('sources.text_to_speech.CHINESE_IMPORT_FOUND', False):
            speech = Speech(enable=False, language="zh")
            self.assertEqual(speech.language, "zh")
            mock_print.assert_called_once()
            args, kwargs = mock_print.call_args
            self.assertIn("cn2an, jieba", args[0])
            self.assertEqual(kwargs['color'], 'warning')

    def test_clean_sentence_en(self):
        speech = Speech(enable=False, language="en")
        text = "Check this out: some/path/to/file.txt"
        cleaned = speech.clean_sentence(text)
        # Should extract filename
        self.assertIn("file.txt", cleaned)

    def test_clean_sentence_zh(self):
        speech = Speech(enable=False, language="zh")
        text = "你好！请看这个：https://example.com/path/to/file.txt"
        cleaned = speech.clean_sentence(text)
        # Should keep Chinese characters and punctuation, remove URL and English
        self.assertIn("你好！", cleaned)
        self.assertNotIn("https", cleaned)
        self.assertNotIn("file.txt", cleaned)

if __name__ == '__main__':
    unittest.main()

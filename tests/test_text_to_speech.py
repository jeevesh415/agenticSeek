import unittest
import shutil
import os
import sys

# Add sources to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sources.text_to_speech import Speech

class TestSpeech(unittest.TestCase):
    def setUp(self):
        self.speech = Speech(enable=False)

    def tearDown(self):
        if os.path.exists(".voices"):
            try:
                shutil.rmtree(".voices")
            except OSError:
                pass

    def test_shorten_paragraph_logic(self):
        # Input text with markdown bold and multiple sentences
        text = "**Explanation**: This is a long explanation. It has multiple sentences.\nNormal line."

        # Expected: ** stripped, and first line truncated to first sentence. Normal line untouched.
        # Note: The punctuation handling might be tricky. Let's assume we want to keep the period.
        expected = "Explanation: This is a long explanation.\nNormal line."

        result = self.speech.shorten_paragraph(text)
        self.assertEqual(result, expected)

    def test_shorten_paragraph_no_bold(self):
        text = "Just a normal line.\nAnother line."
        expected = "Just a normal line.\nAnother line."
        result = self.speech.shorten_paragraph(text)
        self.assertEqual(result, expected)

    def test_clean_sentence_integration(self):
        # This tests if clean_sentence uses shorten_paragraph and preserves the content
        text = "**Explanation**: This is a long explanation. It has multiple sentences."

        # Currently clean_sentence filters out lines starting with **.
        # After fix, it should clean it (remove **) and then keep it.
        cleaned = self.speech.clean_sentence(text)
        self.assertEqual(cleaned, "Explanation: This is a long explanation.")

if __name__ == '__main__':
    unittest.main()

import unittest
import sys
import os

# Ensure the root directory is in the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources.text_to_speech import Speech

class TestSpeechShortenParagraph(unittest.TestCase):
    def setUp(self):
        # Disable enable to not load the pipeline
        self.speech = Speech(enable=False, language="en", voice_idx=0)

    def test_shorten_paragraph_basic(self):
        # We haven't implemented the improved version yet,
        # but let's write tests for the expected behavior.

        # Original simple case
        text = "**Explanation**: This is a long explanation. It has multiple sentences. We only want the first one."
        expected = "**Explanation**: This is a long explanation."
        self.assertEqual(self.speech.shorten_paragraph(text), expected)

    def test_shorten_paragraph_lists(self):
        text = """Here is a list of things:
* First item
* Second item
* Third item
* Fourth item
* Fifth item
* Sixth item"""
        # Expect to keep only the first 3 items or so, and summarize the rest.
        expected = """Here is a list of things:
* First item
* Second item
* Third item
and 3 more items."""
        self.assertEqual(self.speech.shorten_paragraph(text), expected)

    def test_shorten_paragraph_normal_text(self):
        text = "This is normal text. It should not be modified by the shorten paragraph function."
        expected = "This is normal text. It should not be modified by the shorten paragraph function."
        self.assertEqual(self.speech.shorten_paragraph(text), expected)

    def test_shorten_paragraph_long_header_paragraph(self):
        text = "**Summary**: Dr. Smith (Ph.D.) is a doctor. He went to work today! He was very happy."
        expected = "**Summary**: Dr. Smith (Ph.D.) is a doctor."
        self.assertEqual(self.speech.shorten_paragraph(text), expected)

if __name__ == "__main__":
    unittest.main()

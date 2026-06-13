
import unittest
import re
from sources.text_to_speech import Speech

class TestShortenParagraph(unittest.TestCase):
    def setUp(self):
        self.speech = Speech(enable=False)

    def test_bold_explanation(self):
        text = "**Explanation**: This is the core meaning. This is additional context that is not strictly needed for a summary."
        # Expected: Remove bold, keep first sentence because it starts with ** (threshold 1)
        expected = "Explanation: This is the core meaning."
        result = self.speech.shorten_paragraph(text)
        self.assertIn("Explanation: This is the core meaning", result)
        self.assertNotIn("This is additional context", result)

    def test_long_paragraph(self):
        # 4 sentences -> > 3 -> Shorten
        text = "This is the first sentence of a very long paragraph. It has many details that are boring. We should skip them. And more details."
        expected = "This is the first sentence of a very long paragraph."
        result = self.speech.shorten_paragraph(text)
        self.assertIn("This is the first sentence of a very long paragraph", result)
        self.assertNotIn("It has many details", result)

    def test_short_paragraph(self):
        text = "Short text."
        result = self.speech.shorten_paragraph(text)
        self.assertEqual(text, result)

    def test_list_handling(self):
        text = "Here is a list:\n1. Item one\n2. Item two\n3. Item three\n4. Item four"
        # 5 lines total. Threshold > 4. So it should shorten.
        # Kept: Lines 1, 2, 3, 4. Dropped: 5.
        result = self.speech.shorten_paragraph(text)
        self.assertIn("1. Item one", result)
        self.assertIn("3. Item three", result)
        self.assertNotIn("4. Item four", result)
        self.assertIn("... and others", result)

    def test_mixed_content(self):
        # Middle paragraph: 4 sentences -> Shorten.
        text = "**Intro**: Start here.\n\nNext paragraph is long. It goes on. Sentence three. Sentence four.\n\nFinal point."
        result = self.speech.shorten_paragraph(text)
        self.assertIn("Intro: Start here", result)
        self.assertIn("Next paragraph is long", result)
        self.assertNotIn("It goes on", result)
        self.assertIn("Final point", result)

if __name__ == "__main__":
    unittest.main()

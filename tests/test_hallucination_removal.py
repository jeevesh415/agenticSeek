import sys
import unittest
from unittest.mock import MagicMock
import re

# Mock heavy dependencies before import
sys.modules['torch'] = MagicMock()
sys.modules['librosa'] = MagicMock()
sys.modules['pyaudio'] = MagicMock()
sys.modules['transformers'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['colorama'] = MagicMock()

from sources.speech_to_text import Transcript

class TestHallucinationRemoval(unittest.TestCase):
    def setUp(self):
        # Patch init to avoid loading models
        Transcript.__init__ = lambda self: None
        self.transcriber = Transcript()

    def test_valid_sentences(self):
        """Test sentences that contain hallucination trigger words but are valid."""
        valid_cases = [
            "I see you.",
            "Are you going to the store?",
            "I am going to.",
            "Oh, really?",
            "Mh-hmm, yes.",
            "This is not correct.",
            "Thank you for your help.",
            "Okay, I will do that.",
            "You are doing great."
        ]

        for case in valid_cases:
            result = self.transcriber.remove_hallucinations(case)
            self.assertEqual(result.strip(), case, f"Failed on valid case: '{case}' -> '{result}'")

    def test_common_hallucinations(self):
        """Test removal of common Whisper hallucinations."""
        hallucination_cases = [
            ("Thank you for watching.", ""),
            ("Thank you for watching", ""),
            ("Thanks for watching.", ""),
            ("Thanks for watching!", ""),
            ("Please subscribe to my channel.", ""),
            ("Subscribe for more.", ""),
            ("Subtitle by Amara.org", ""),
            ("Subtitles by Amara.org", ""),
            ("Translated by Amara.org", ""),
            ("Okay.", ""),
            ("Hmm.", ""),
            ("Uh", ""),
            ("Thank you.", ""),
            ("Thank you", "")
        ]

        for case, expected in hallucination_cases:
            result = self.transcriber.remove_hallucinations(case)
            self.assertEqual(result.strip(), expected, f"Failed on hallucination: '{case}' -> '{result}'")

    def test_mixed_sentences(self):
        """Test valid speech mixed with hallucinations."""
        mixed_cases = [
            ("I went to the store today. Thank you for watching.", "I went to the store today."),
            ("Okay. Let's get started.", "Let's get started."),
            ("Uh, I don't know. Hmm.", "I don't know."),
            ("Subtitles by Amara.org The quick brown fox.", "The quick brown fox."),
            ("The quick brown fox. Subtitles by Amara.org", "The quick brown fox.")
        ]

        for case, expected in mixed_cases:
            result = self.transcriber.remove_hallucinations(case)
            # We might have extra spaces, so let's normalize them for comparison
            normalized_result = re.sub(r'\s+', ' ', result).strip()
            self.assertEqual(normalized_result, expected, f"Failed on mixed case: '{case}' -> '{result}'")

    def test_repetitive_hallucinations(self):
        """Test removal of stuttering/loops common in Whisper."""
        repetitive_cases = [
            ("you. you. you.", ""),
            ("No no no.", ""),
            ("Yes! Yes! Yes!", ""),
            ("I went to the the the store.", "I went to store."), # Note: this removes "the the the " leaving "I went to store."
            ("I went you you you to the store.", "I went to the store.")
        ]

        for case, expected in repetitive_cases:
            result = self.transcriber.remove_hallucinations(case)
            normalized_result = re.sub(r'\s+', ' ', result).strip()
            self.assertEqual(normalized_result, expected, f"Failed on repetitive case: '{case}' -> '{result}'")

if __name__ == '__main__':
    unittest.main()

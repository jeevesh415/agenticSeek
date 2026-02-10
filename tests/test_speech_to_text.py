import unittest
from unittest.mock import MagicMock
import sys
import os

# Mock all dependencies inside the try-except block of sources.speech_to_text
# This ensures that the try block succeeds and pyaudio is available for the class definition
sys.modules['pyaudio'] = MagicMock()
sys.modules['pyaudio'].paInt16 = 1
sys.modules['torch'] = MagicMock()
sys.modules['librosa'] = MagicMock()
sys.modules['transformers'] = MagicMock()

# Ensure sources is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sources.speech_to_text import Transcript

class TestSpeechToText(unittest.TestCase):
    def setUp(self):
        # Patch __init__ to avoid model loading
        self.original_init = Transcript.__init__
        Transcript.__init__ = lambda self: None
        self.transcript = Transcript()

    def tearDown(self):
        Transcript.__init__ = self.original_init

    def test_remove_hallucinations_artifacts(self):
        """Test removal of common artifacts."""
        artifacts = [
            "Thank you for watching.",
            "Subtitle by Amara.org"
        ]
        for text in artifacts:
            cleaned = self.transcript.remove_hallucinations(text)
            self.assertEqual(cleaned, "", f"Failed to remove artifact: {text}")

    def test_remove_hallucinations_silence_fragments(self):
        """Test removal of silence fragments."""
        fragments = [
            "you",
            "not.",
            "going to."
        ]
        for text in fragments:
            cleaned = self.transcript.remove_hallucinations(text)
            self.assertEqual(cleaned, "", f"Failed to remove fragment: {text}")

    def test_preserve_valid_sentences(self):
        """Test that valid sentences are preserved."""
        valid_sentences = [
            ("Do you want to go?", "Do you want to go?"),
            ("I am not.", "I am not."),
            ("Oh, I see.", "Oh, I see."),
            ("You're welcome.", "You're welcome."),
            ("Okay. Let's start.", "Okay. Let's start."),
            ("This is going to be fun.", "This is going to be fun."),
             ("Thank you.", "Thank you.")
        ]
        for original, expected in valid_sentences:
            cleaned = self.transcript.remove_hallucinations(original)
            self.assertEqual(cleaned, expected, f"Incorrectly modified valid sentence: {original}")

if __name__ == '__main__':
    unittest.main()

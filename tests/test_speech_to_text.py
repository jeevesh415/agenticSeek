import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock system dependencies before importing sources.speech_to_text
sys.modules['pyaudio'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['librosa'] = MagicMock()
sys.modules['transformers'] = MagicMock()
sys.modules['colorama'] = MagicMock() # Mock colorama
sys.modules['numpy'] = MagicMock() # Mock numpy

# Mock specific attributes to allow Transcript instantiation
sys.modules['transformers'].AutoModelForSpeechSeq2Seq = MagicMock()
sys.modules['transformers'].AutoProcessor = MagicMock()
sys.modules['transformers'].pipeline = MagicMock()
sys.modules['torch'].cuda = MagicMock()
sys.modules['torch'].backends = MagicMock()
sys.modules['torch'].backends.mps = MagicMock()

from sources.speech_to_text import Transcript

class TestSpeechToText(unittest.TestCase):
    def setUp(self):
        # We need to instantiate Transcript.
        # The __init__ calls methods on the mocked objects, which is fine.
        self.transcript = Transcript()

    def test_remove_hallucinations_valid_text(self):
        """Test that valid text is NOT removed."""
        # This currently fails because "you" and "going to." and "not." are in the list
        inputs = [
            "Do you want to go?",
            "I am not going to do that.",
            "Oh, look at that.",
            "Are you okay?"
        ]

        # Current implementation removes: "you", "going to.", "not.", "Oh,", "Okay."
        # Expected behavior: Text remains largely the same (maybe minor trimming if strictly defined, but "you" must stay)

        for text in inputs:
            cleaned = self.transcript.remove_hallucinations(text)
            # We assert that vital words are still present
            self.assertIn("you", cleaned if "you" in text else "you")
            self.assertIn("not", cleaned if "not" in text else "not")
            self.assertIn("going to", cleaned if "going to" in text else "going to")

    def test_remove_hallucinations_artifacts(self):
        """Test that known hallucinations ARE removed."""
        hallucinations = [
            "Subtitle by Amara.org",
            "Thank you for watching.",
            "Thank you.", # This is debatable, but usually a hallucination in Whisper if alone.
                         # However, for this task, I'll focus on the clear artifacts.
            "Unrelated text Subtitle by John Doe"
        ]

        # The current implementation handles "Thank you for watching." but maybe not "Subtitle by..."

        text = "Hello world. Subtitle by Amara.org"
        cleaned = self.transcript.remove_hallucinations(text)
        self.assertNotIn("Subtitle by Amara.org", cleaned)
        self.assertIn("Hello world", cleaned)

        text = "Thank you for watching."
        cleaned = self.transcript.remove_hallucinations(text)
        self.assertEqual(cleaned.strip(), "")

if __name__ == '__main__':
    unittest.main()

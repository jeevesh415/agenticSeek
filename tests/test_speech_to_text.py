import unittest
from unittest.mock import MagicMock, patch
import sys

# We need to ensure dependencies are safely mocked if missing, but without
# irreversibly polluting the environment of other tests if run in a suite.
class TestSpeechToText(unittest.TestCase):

    def setUp(self):
        # We mock these only for the duration of the test run to avoid breaking other test modules
        # that might actually need real imports if they are available in their test environments.
        self.patchers = [
            patch.dict(sys.modules, {
                'torch': MagicMock(),
                'librosa': MagicMock(),
                'pyaudio': MagicMock(),
                'transformers': MagicMock(),
                'numpy': MagicMock(),
            })
        ]

        # Setup colorama mock specifically
        colorama_mock = MagicMock()
        colorama_mock.Fore.RED = ''
        colorama_mock.Fore.GREEN = ''
        colorama_mock.Fore.YELLOW = ''
        colorama_mock.Fore.BLUE = ''
        colorama_mock.Fore.RESET = ''
        self.patchers.append(patch.dict(sys.modules, {'colorama': colorama_mock}))

        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in self.patchers:
            p.stop()

    @patch('sources.speech_to_text.Transcript.__init__', return_value=None)
    def test_remove_hallucinations(self, mock_init):
        # Late import after setting up mocks
        from sources.speech_to_text import Transcript

        # Initialize Transcript without calling original __init__ (avoids heavy model loading)
        transcript = Transcript()

        # Test basic hallucination removal
        self.assertEqual(transcript.remove_hallucinations("Thank you for watching."), "")
        self.assertEqual(transcript.remove_hallucinations("Okay. Thank you."), "")
        self.assertEqual(transcript.remove_hallucinations("Oh, you are not."), "are")

        # Test case insensitivity
        self.assertEqual(transcript.remove_hallucinations("tHaNk YoU"), "")
        self.assertEqual(transcript.remove_hallucinations("OKAY."), "")

        # Test word boundaries (should not remove substrings of valid words like "Ohio" or "youth")
        self.assertEqual(transcript.remove_hallucinations("your youth is yours"), "your youth is yours")
        self.assertEqual(transcript.remove_hallucinations("Ohio is a state"), "Ohio is a state")

        # Test repetitive word loop removal
        self.assertEqual(transcript.remove_hallucinations("Hello hello hello world world"), "Hello world")
        self.assertEqual(transcript.remove_hallucinations("The the the car car is fast fast fast."), "The car is fast.")
        self.assertEqual(transcript.remove_hallucinations("I am am very very very tired tired."), "I am very tired.")

        # Test combination of hallucinations and normal text
        self.assertEqual(
            transcript.remove_hallucinations("Okay. Hello hello world. Thank you."),
            "Hello world."
        )

if __name__ == '__main__':
    unittest.main()

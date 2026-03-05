import unittest

from sources.advanced_capabilities import suggest_capability_guidance


class TestAdvancedCapabilities(unittest.TestCase):
    def test_matches_multiple_tracks(self):
        goal = "Build an AGI workflow with memory, tools, and safety guardrails in production"
        guidance = suggest_capability_guidance(goal)
        self.assertGreaterEqual(len(guidance), 3)
        joined = " ".join(guidance).lower()
        self.assertIn("guardrails", joined)
        self.assertIn("retrieval", joined)

    def test_falls_back_when_no_trigger(self):
        guidance = suggest_capability_guidance("hello there")
        self.assertGreaterEqual(len(guidance), 1)
        self.assertIn("modular architecture", guidance[0].lower())


if __name__ == "__main__":
    unittest.main()

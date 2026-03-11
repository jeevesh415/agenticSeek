import sys
import os

# Create mock for missing heavy modules if we want to run tests faster,
# but since the PR is modifying standard python list comprehensions, we can just run a python test.
from sources.router import AgentRouter

def test_router_learn_few_shots():
    # We will use mock models to ensure that add_examples is called properly
    class MockClassifier:
        def __init__(self):
            self.examples = []
        def add_examples(self, texts, labels):
            self.examples.append((texts, labels))
            # verify they are actually lists
            assert isinstance(texts, list)
            assert isinstance(labels, list)

    class MockPipeline:
        pass

    class MockLanguageUtility:
        def __init__(self, *args, **kwargs):
            pass

    # Create a dummy AgentRouter without initializing heavy pipelines
    router = AgentRouter.__new__(AgentRouter)
    router.talk_classifier = MockClassifier()
    router.complexity_classifier = MockClassifier()

    router.learn_few_shots_tasks()
    router.learn_few_shots_complexity()

    print("learn_few_shots_tasks and learn_few_shots_complexity executed successfully with lists.")

if __name__ == "__main__":
    test_router_learn_few_shots()

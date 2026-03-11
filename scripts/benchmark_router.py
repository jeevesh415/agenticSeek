import timeit
import random

def setup_data(size):
    labels = ["LOW", "HIGH", "coding", "web", "files", "talk", "code", "mcp"]
    return [(f"Example sentence {i}", random.choice(labels)) for i in range(size)]

def test_list_comprehension(data):
    texts = [text for text, _ in data]
    labels = [label for _, label in data]
    return texts, labels

def test_zip_list(data):
    texts, labels = list(zip(*data))
    return list(texts), list(labels)

def test_zip_unpack(data):
    texts, labels = zip(*data)
    return list(texts), list(labels)

def run_benchmark():
    data_small = setup_data(100) # Similar size to router.py
    data_large = setup_data(10000)

    print("--- Small dataset (100 items) ---")
    time_comp_small = timeit.timeit(lambda: test_list_comprehension(data_small), number=10000)
    time_zip_list_small = timeit.timeit(lambda: test_zip_list(data_small), number=10000)
    time_zip_unpack_small = timeit.timeit(lambda: test_zip_unpack(data_small), number=10000)

    print(f"List Comprehension: {time_comp_small:.5f}s")
    print(f"list() and list(): {time_zip_list_small:.5f}s")
    print(f"zip unpack list(): {time_zip_unpack_small:.5f}s")

    print("\n--- Large dataset (10000 items) ---")
    time_comp_large = timeit.timeit(lambda: test_list_comprehension(data_large), number=1000)
    time_zip_list_large = timeit.timeit(lambda: test_zip_list(data_large), number=1000)
    time_zip_unpack_large = timeit.timeit(lambda: test_zip_unpack(data_large), number=1000)

    print(f"List Comprehension: {time_comp_large:.5f}s")
    print(f"list() and list(): {time_zip_list_large:.5f}s")
    print(f"zip unpack list(): {time_zip_unpack_large:.5f}s")

if __name__ == "__main__":
    run_benchmark()

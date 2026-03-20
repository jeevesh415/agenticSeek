import timeit
import random

def setup_data(size=1000):
    search_history_list = [f"http://example.com/{i}" for i in range(size)]
    search_history_set = set(search_history_list)

    # 50% visited, 50% unvisited
    search_result = [
        {"link": f"http://example.com/{i}", "title": f"Title {i}"} for i in range(size // 2)
    ] + [
        {"link": f"http://example.com/new_{i}", "title": f"New Title {i}"} for i in range(size // 2)
    ]
    random.shuffle(search_result)

    return search_history_list, search_history_set, search_result

def benchmark_select_unvisited_list(search_history, search_result):
    results_unvisited = []
    for res in search_result:
        if res["link"] not in search_history:
            results_unvisited.append(res)
    return results_unvisited

def benchmark_select_unvisited_set_comprehension(search_history, search_result):
    return [res for res in search_result if res["link"] not in search_history]

def run_benchmark():
    sizes = [100, 1000]

    for size in sizes:
        print(f"\nBenchmarking with {size} links:")
        setup_code = f"""
from __main__ import setup_data, benchmark_select_unvisited_list, benchmark_select_unvisited_set_comprehension
search_history_list, search_history_set, search_result = setup_data({size})
        """

        stmt_list = "benchmark_select_unvisited_list(search_history_list, search_result)"
        stmt_set = "benchmark_select_unvisited_set_comprehension(search_history_set, search_result)"

        list_time = timeit.timeit(stmt_list, setup=setup_code, number=100)
        set_time = timeit.timeit(stmt_set, setup=setup_code, number=100)

        print(f"Original (List + loop) time:   {list_time:.4f} seconds")
        print(f"Optimized (Set + comp) time: {set_time:.4f} seconds")
        if set_time > 0:
            print(f"Improvement: {list_time / set_time:.2f}x faster")

if __name__ == "__main__":
    run_benchmark()

import timeit

def run_benchmark():
    setup_code = """
ai_name = "jarvis"
text = "Hello there Jarvis, how are you doing today? I would like you to execute the program."
trigger_words = {
    'EN': [f"{ai_name}", "hello", "hi"],
    'FR': [f"{ai_name}", "hello", "hi"],
    'ZH': [f"{ai_name}", "hello", "hi"],
    'ES': [f"{ai_name}", "hello", "hi"]
}
confirmation_words = {
    'EN': ["do it", "go ahead", "execute", "run", "start", "thanks", "would ya", "please", "okay?", "proceed", "continue", "go on", "do that", "go it", "do you understand?"],
    'FR': ["fais-le", "vas-y", "exécute", "lance", "commence", "merci", "tu veux bien", "s'il te plaît", "d'accord ?", "poursuis", "continue", "vas-y", "fais ça", "compris"],
    'ZH_CHT': ["做吧", "繼續", "執行", "運作看看", "開始", "謝謝", "可以嗎", "請", "好嗎", "進行", "做吧", "go", "do it", "執行吧", "懂了"],
    'ZH_SC': ["做吧", "继续", "执行", "运作看看", "开始", "谢谢", "可以吗", "请", "好吗", "运行", "做吧", "go", "do it", "执行吧", "懂了"],
    'ES': ["hazlo", "adelante", "ejecuta", "corre", "empieza", "gracias", "lo harías", "por favor", "¿vale?", "procede", "continúa", "sigue", "haz eso", "haz esa cosa"]
}
"""

    test_unoptimized = """
recorded = ""
done = False
for language, words in trigger_words.items():
    if any(word in text.lower() for word in words):
        recorded = text
for language, words in confirmation_words.items():
    if any(word in text.lower() for word in words):
        done = True
        break
"""

    test_optimized = """
recorded = ""
done = False
text_lower = text.lower()
for language, words in trigger_words.items():
    if any(word in text_lower for word in words):
        recorded = text
for language, words in confirmation_words.items():
    if any(word in text_lower for word in words):
        done = True
        break
"""

    iterations = 100000

    time_unoptimized = timeit.timeit(stmt=test_unoptimized, setup=setup_code, number=iterations)
    time_optimized = timeit.timeit(stmt=test_optimized, setup=setup_code, number=iterations)

    print(f"Iterations: {iterations}")
    print(f"Unoptimized time: {time_unoptimized:.4f} seconds")
    print(f"Optimized time:   {time_optimized:.4f} seconds")
    print(f"Improvement:      {(time_unoptimized - time_optimized) / time_unoptimized * 100:.2f}% faster")

if __name__ == "__main__":
    run_benchmark()


try:
    from colorama import Fore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    class _Fore:
        GREEN = RED = LIGHTGREEN_EX = LIGHTBLUE_EX = YELLOW = LIGHTCYAN_EX = RESET = CYAN = ""
    Fore = _Fore()

try:
    from termcolor import colored
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    def colored(text, _color):
        return text
import platform
import threading
import itertools
import time

thinking_event = threading.Event()
current_animation_thread = None

def get_color_map():
    if platform.system().lower() != "windows":
        color_map = {
            "success": "green",
            "failure": "red",
            "status": "light_green",
            "code": "light_blue",
            "warning": "yellow",
            "output": "cyan",
            "info": "cyan"
        }
    else:
        color_map = {
            "success": "green",
            "failure": "red",
            "status": "light_green",
            "code": "light_blue",
            "warning": "yellow",
            "output": "cyan",
            "info": "black"
        }
    return color_map

def pretty_print(text, color="info", no_newline=False):
    """
    Print text with color formatting.

    Args:
        text (str): The text to print
        color (str, optional): The color to use. Defaults to "info".
            Valid colors are:
            - "success": Green
            - "failure": Red 
            - "status": Light green
            - "code": Light blue
            - "warning": Yellow
            - "output": Cyan
            - "default": Black (Windows only)
    """
    thinking_event.set()
    if current_animation_thread and current_animation_thread.is_alive():
        current_animation_thread.join()
    thinking_event.clear()
    
    color_map = get_color_map()
    if color not in color_map:
        color = "info"
    print(colored(text, color_map[color]), end='' if no_newline else "\n")

def animate_thinking(text, color="status", duration=120):
    """
    Animate a thinking spinner while a task is being executed.
    It use a daemon thread to run the animation. This will not block the main thread.
    Color are the same as pretty_print.
    """
    global current_animation_thread
    
    thinking_event.set()
    if current_animation_thread and current_animation_thread.is_alive():
        current_animation_thread.join()
    thinking_event.clear()
    
    def _animate():
        color_map = {
            "success": (Fore.GREEN, "green"),
            "failure": (Fore.RED, "red"),
            "status": (Fore.LIGHTGREEN_EX, "light_green"),
            "code": (Fore.LIGHTBLUE_EX, "light_blue"),
            "warning": (Fore.YELLOW, "yellow"),
            "output": (Fore.LIGHTCYAN_EX, "cyan"),
            "default": (Fore.RESET, "black"),
            "info": (Fore.CYAN, "cyan")
        }
        fore_color, term_color = color_map.get(color, color_map["default"])
        spinner = itertools.cycle([
            '▉▁▁▁▁▁', '▉▉▂▁▁▁', '▉▉▉▃▁▁', '▉▉▉▉▅▁', '▉▉▉▉▉▇', '▉▉▉▉▉▉',
            '▉▉▉▉▇▅', '▉▉▉▆▃▁', '▉▉▅▃▁▁', '▉▇▃▁▁▁', '▇▃▁▁▁▁', '▃▁▁▁▁▁',
            '▁▃▅▃▁▁', '▁▅▉▅▁▁', '▃▉▉▉▃▁', '▅▉▁▉▅▃', '▇▃▁▃▇▅', '▉▁▁▁▉▇',
            '▉▅▃▁▃▅', '▇▉▅▃▅▇', '▅▉▇▅▇▉', '▃▇▉▇▉▅', '▁▅▇▉▇▃', '▁▃▅▇▅▁' 
        ])
        end_time = time.time() + duration

        while not thinking_event.is_set() and time.time() < end_time:
            symbol = next(spinner)
            if platform.system().lower() != "windows":
                print(f"\r{fore_color}{symbol} {text}{Fore.RESET}", end="", flush=True)
            else:
                print(f"\r{colored(f'{symbol} {text}', term_color)}", end="", flush=True)
            time.sleep(0.2)
        print("\r" + " " * (len(text) + 7) + "\r", end="", flush=True)
    current_animation_thread = threading.Thread(target=_animate, daemon=True)
    current_animation_thread.start()

def timer_decorator(func):
    """
    Decorator to measure the execution time of a function.
    Usage:
    @timer_decorator
    def my_function():
        # code to execute
    """
    from time import time
    def wrapper(*args, **kwargs):
        start_time = time()
        result = func(*args, **kwargs)
        end_time = time()
        pretty_print(f"{func.__name__} took {end_time - start_time:.2f} seconds to execute", "status")
        return result
    return wrapper

if __name__ == "__main__":
    import time
    pretty_print("starting imaginary task", "success")
    animate_thinking("Thinking...", "status")
    time.sleep(4)
    pretty_print("starting another task", "failure")
    animate_thinking("Thinking...", "status")
    time.sleep(4)
    pretty_print("yet another task", "info")
    animate_thinking("Thinking...", "status")
    time.sleep(4)
    pretty_print("This is an info message", "info")
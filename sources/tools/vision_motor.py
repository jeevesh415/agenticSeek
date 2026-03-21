import os
import time
import base64
import logging
from io import BytesIO
from typing import List, Tuple, Dict

try:
    import pyautogui
    import mss
    import mss.tools
except ImportError:
    pyautogui = None
    mss = None

from sources.tools.tools import Tools

logger = logging.getLogger(__name__)

class VisionMotorAutomation(Tools):
    """
    Vision-Motor UI Automation (VPT-style).
    Provides the AGI with the ability to "see" the computer screen via screenshots,
    process visual elements, and directly control the mouse/keyboard using absolute coordinates
    to operate arbitrary desktop software (Photoshop, CAD, Games) exactly like a human.
    """
    def __init__(self, dry_run: bool = True, output_dir: str = ".screenshots"):
        super().__init__()
        self.name = "vision_motor"
        self.description = "Look at the screen, move the mouse, click coordinates, and type keys."
        self.dry_run = dry_run
        self.output_dir = output_dir

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        if not pyautogui or not mss:
            logger.warning("[VisionMotor] pyautogui or mss not installed. Operating in SIMULATION mode.")
            self.dry_run = True

    def execute(self, blocks: List[str]) -> str:
        """Executes a sequence of visual-motor commands."""
        if not blocks:
            return "No command provided."

        command_line = blocks[0].strip()
        parts = command_line.split(" ", 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command == "look":
            return self._capture_screen()
        elif command == "click":
            return self._click_mouse(args)
        elif command == "type":
            return self._type_keys(args)
        elif command == "drag":
            return self._drag_mouse(args)
        else:
            return f"Error: Unknown vision-motor command '{command}'. Available: look, click [x,y], type [text], drag [x1,y1,x2,y2]."

    def _capture_screen(self) -> str:
        """Takes a screenshot of the primary monitor and returns the file path and a base64 summary."""
        if self.dry_run or not mss:
            return "[SIMULATION: DRY-RUN] Captured screen successfully. Resolution: 1920x1080. Returning simulated base64 string."

        filepath = os.path.join(self.output_dir, f"vision_motor_{int(time.time())}.png")
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1] # Primary monitor
                sct_img = sct.grab(monitor)
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=filepath)

            # In a full AGI, the vision-enabled LLM parses this image directly.
            # Here we return the path so the multimodal agent can attach it to its context.
            return f"Screen captured successfully to {filepath}. Analyze the visual layout before deciding the next coordinate to click."
        except Exception as e:
            return f"Failed to capture screen: {e}"

    def _click_mouse(self, args: str) -> str:
        """Moves the mouse to an absolute coordinate and clicks."""
        try:
            coords = args.split(",")
            x = int(coords[0].strip())
            y = int(coords[1].strip())
        except (ValueError, IndexError):
            return "Error: Invalid coordinates. Format must be 'x, y' (e.g., click 500, 300)."

        if self.dry_run or not pyautogui:
            return f"[SIMULATION: DRY-RUN] Mouse moved to ({x}, {y}) and clicked."

        try:
            # Human-like tweening for the mouse movement (ease-in-out)
            pyautogui.moveTo(x, y, duration=0.5, tween=pyautogui.easeInOutQuad)
            pyautogui.click()
            return f"Successfully clicked at ({x}, {y})."
        except Exception as e:
            return f"Failed to click mouse: {e}"

    def _type_keys(self, text: str) -> str:
        """Simulates human typing on the keyboard."""
        if not text:
            return "Error: No text provided to type."

        if self.dry_run or not pyautogui:
            return f"[SIMULATION: DRY-RUN] Typed the following text: '{text}'"

        try:
            # Type with a slight random delay between keystrokes to simulate human speed
            pyautogui.write(text, interval=0.05)
            return f"Successfully typed text."
        except Exception as e:
            return f"Failed to type text: {e}"

    def _drag_mouse(self, args: str) -> str:
        """Drags the mouse from one coordinate to another."""
        try:
            coords = args.split(",")
            x1, y1 = int(coords[0].strip()), int(coords[1].strip())
            x2, y2 = int(coords[2].strip()), int(coords[3].strip())
        except (ValueError, IndexError):
            return "Error: Invalid coordinates. Format must be 'x1, y1, x2, y2'."

        if self.dry_run or not pyautogui:
            return f"[SIMULATION: DRY-RUN] Dragged mouse from ({x1}, {y1}) to ({x2}, {y2})."

        try:
            pyautogui.moveTo(x1, y1, duration=0.2)
            pyautogui.dragTo(x2, y2, duration=0.5, button='left')
            return f"Successfully dragged from ({x1}, {y1}) to ({x2}, {y2})."
        except Exception as e:
            return f"Failed to drag mouse: {e}"

    def load_exec_block(self, text: str) -> Tuple[List[str], str]:
        """Parses a vision_motor block from the agent's text response."""
        blocks = []
        in_block = False
        current_block = []

        for line in text.split('\n'):
            if line.strip().startswith('```vision_motor'):
                in_block = True
                current_block = []
            elif line.strip() == '```' and in_block:
                in_block = False
                blocks.append('\n'.join(current_block))
            elif in_block:
                current_block.append(line)

        return blocks if blocks else None, None

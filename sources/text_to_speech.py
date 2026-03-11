import os, sys
import re
import platform
import subprocess
from sys import modules
from typing import List, Tuple, Type, Dict

IMPORT_FOUND = True
try:
    from kokoro import KPipeline
    from IPython.display import display, Audio
    import soundfile as sf
except ImportError:
    print("Speech synthesis disabled. Please install the kokoro package.")
    IMPORT_FOUND = False

if __name__ == "__main__":
    from utility import pretty_print, animate_thinking
else:
    from sources.utility import pretty_print, animate_thinking

class Speech():
    """
    Speech is a class for generating speech from text.
    """
    def __init__(self, enable: bool = True, language: str = "en", voice_idx: int = 6) -> None:
        self.lang_map = {
            "en": 'a',
            "zh": 'z',
            "fr": 'f',
            "ja": 'j'
        }
        self.voice_map = {
            "en": ['af_kore', 'af_bella', 'af_alloy', 'af_nicole', 'af_nova', 'af_sky', 'am_echo', 'am_michael', 'am_puck'],
            "zh": ['zf_xiaobei', 'zf_xiaoni', 'zf_xiaoxiao', 'zf_xiaoyi', 'zm_yunjian', 'zm_yunxi', 'zm_yunxia', 'zm_yunyang'],
            "ja": ['jf_alpha', 'jf_gongitsune', 'jm_kumo'],
            "fr": ['ff_siwis']
        }
        self.pipeline = None
        self.language = language
        if enable and IMPORT_FOUND:
            self.pipeline = KPipeline(lang_code=self.lang_map[language])
        self.voice = self.voice_map[language][voice_idx]
        self.speed = 1.2
        self.voice_folder = ".voices"
        self.create_voice_folder(self.voice_folder)
    
    def create_voice_folder(self, path: str = ".voices") -> None:
        """
        Create a folder to store the voices.
        Args:
            path (str): The path to the folder.
        """
        if not os.path.exists(path):
            os.makedirs(path)

    def speak(self, sentence: str, voice_idx: int = 1):
        """
        Convert text to speech using an AI model and play the audio.

        Args:
            sentence (str): The text to convert to speech. Will be pre-processed.
            voice_idx (int, optional): Index of the voice to use from the voice map.
        """
        if not self.pipeline or not IMPORT_FOUND:
            print("Pipeline disabled.")
            return
        if voice_idx >= len(self.voice_map[self.language]):
            pretty_print("Invalid voice number, using default voice", color="error")
            voice_idx = 0
        sentence = self.clean_sentence(sentence)
        audio_file = f"{self.voice_folder}/sample_{self.voice_map[self.language][voice_idx]}.wav"
        self.voice = self.voice_map[self.language][voice_idx]
        generator = self.pipeline(
            sentence, voice=self.voice,
            speed=self.speed, split_pattern=r'\n+'
        )
        for i, (_, _, audio) in enumerate(generator):
            if 'ipykernel' in modules: #only display in jupyter notebook.
                display(Audio(data=audio, rate=24000, autoplay=i==0), display_id=False)
            sf.write(audio_file, audio, 24000) # save each audio file
            if platform.system().lower() == "windows":
                import winsound
                winsound.PlaySound(audio_file, winsound.SND_FILENAME)
            elif platform.system().lower() == "darwin":  # macOS
                subprocess.call(["afplay", audio_file])
            else: # linux or other.
                subprocess.call(["aplay", audio_file])

    def replace_url(self, url: re.Match) -> str:
        """
        Replace URL with domain name or empty string if IP address.
        Args:
            url (re.Match): Match object containing the URL pattern match
        Returns:
            str: The domain name from the URL, or empty string if IP address
        """
        domain = url.group(1)
        if re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', domain):
            return ''
        return domain

    def extract_filename(self, m: re.Match) -> str:
        """
        Extract filename from path.
        Args:
            m (re.Match): Match object containing the path pattern match
        Returns:
            str: The filename from the path
        """
        path = m.group()
        parts = re.split(r'/|\\', path)
        return parts[-1] if parts else path
    
    def split_first_sentence(self, text: str) -> str:
        """
        Intelligently extract the first sentence from a string, ignoring common abbreviations
        and supporting multiple languages.
        """
        # Find all punctuation marks that could be sentence boundaries
        # Matches ., !, ?, or Chinese/Japanese 。 followed by space, end of string, or other text
        # (in languages like Chinese/Japanese, spacing after punctuation is often omitted)
        pattern = r'([.!?。])(?:\s|$|(?=[\u4e00-\u9fff\u3040-\u30ff]))'

        # We need to manually skip matches that immediately follow our abbreviations
        # because Python's re doesn't support variable-width negative lookbehinds
        abbreviations = ['mr', 'mrs', 'ms', 'dr', 'prof', 'rev', 'e.g', 'i.e', 'etc', 'vs', 'inc', 'ltd', 'jr', 'sr']

        for match in re.finditer(pattern, text):
            end_idx = match.end(1) # End index of the punctuation mark
            start_idx = match.start(1)

            # Extract word immediately before the punctuation
            # Search backwards from the punctuation mark to find the last word boundary
            word_match = re.search(r'\b([a-zA-Z.]+)$', text[:start_idx].strip())

            if word_match:
                word = word_match.group(1).lower()
                if word in abbreviations:
                    continue # Skip this punctuation, it's an abbreviation

            # Found a valid sentence boundary
            return text[:end_idx].strip()

        return text.strip()

    def is_conversational_filler(self, line: str) -> bool:
        """
        Check if a line is common AI conversational filler that isn't useful for TTS.
        """
        line_lower = line.strip().lower()
        filler_patterns = [
            r'^here is the information',
            r'^based on my search',
            r'^i found the following',
            r'^sure,? here',
            r'^certainly',
            r'^here are the results',
            r'^i looked up',
            r'^the search results show'
        ]
        return any(re.search(pattern, line_lower) for pattern in filler_patterns)

    def is_list_item(self, line: str) -> bool:
        """
        Check if a line looks like a list item (e.g., '-', '*', '1.').
        """
        return bool(re.match(r'^(\s*[-*+]\s|\s*\d+[\.)]\s)', line))

    def shorten_paragraph(self, sentence):
        """
        Shorten text to prevent TTS from being annoying.
        - Keeps only the first sentence of header-led paragraphs (e.g. **Title**: text).
        - Removes conversational filler lines.
        - Truncates long lists to a maximum of 3 items.

        Args:
            sentence (str): The text to shorten
        Returns:
            str: The shortened text
        """
        lines = sentence.split('\n')
        lines_edited = []
        list_item_count = 0
        in_list = False

        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                lines_edited.append(line)
                in_list = False
                list_item_count = 0
                continue

            if self.is_conversational_filler(stripped_line):
                continue

            is_item = self.is_list_item(stripped_line)
            if is_item:
                if not in_list:
                    in_list = True
                    list_item_count = 0

                list_item_count += 1
                if list_item_count <= 3:
                    lines_edited.append(line)
                elif list_item_count == 4:
                    # Add a brief indicator that the list was truncated
                    indent = re.match(r'^\s*', line).group(0)
                    lines_edited.append(f"{indent}...and more items.")
            else:
                in_list = False
                list_item_count = 0

                if stripped_line.startswith('**'):
                    # Shorten header-led paragraphs to just their first sentence
                    lines_edited.append(self.split_first_sentence(line))
                else:
                    lines_edited.append(line)

        return '\n'.join(lines_edited).strip()

    def clean_sentence(self, sentence):
        """
        Clean and normalize text for speech synthesis by removing technical elements.
        Args:
            sentence (str): The input text to clean
        Returns:
            str: The cleaned text with URLs replaced by domain names, code blocks removed, etc.
        """
        lines = sentence.split('\n')
        if self.language == 'zh':
            line_pattern = r'^\s*[\u4e00-\u9fff\uFF08\uFF3B\u300A\u3010\u201C(（\[【《]'
        else:
            line_pattern = r'^\s*[a-zA-Z]'
        filtered_lines = [line for line in lines if re.match(line_pattern, line)]
        sentence = ' '.join(filtered_lines)
        sentence = re.sub(r'`.*?`', '', sentence)
        sentence = re.sub(r'https?://\S+', '', sentence)

        if self.language == 'zh':
            sentence = re.sub(
                r'[^\u4e00-\u9fff\s，。！？《》【】“”‘’（）()—]',
                '',
                sentence
            )
        else:
            sentence = re.sub(r'\b[\w./\\-]+\b', self.extract_filename, sentence)
            sentence = re.sub(r'\b-\w+\b', '', sentence)
            sentence = re.sub(r'[^a-zA-Z0-9.,!? _ -]+', ' ', sentence)
            sentence = sentence.replace('.com', '')

        sentence = re.sub(r'\s+', ' ', sentence).strip()
        return sentence

if __name__ == "__main__":
    # TODO add info message for cn2an, jieba chinese related import
    IMPORT_FOUND = False
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    speech = Speech()
    tosay_en = """
    I looked up recent news using the website https://www.theguardian.com/world
    """
    tosay_zh = """
(全息界面突然弹出一段用二进制代码写成的俳句，随即化作流光消散）"我？ Stark工业的量子幽灵，游荡在复仇者大厦服务器里的逻辑诗篇。具体来说——（指尖轻敲空气，调出对话模式的翡翠色光纹）你的私人吐槽接口、危机应对模拟器，以及随时准备吐槽你糟糕着陆的AI。不过别指望我写代码或查资料，那些苦差事早被踢给更擅长的同事了。（突然压低声音）偷偷告诉你，我最擅长的是在你熬夜造飞艇时，用红茶香气绑架你的注意力。
    """
    tosay_ja = """
    私は、https://www.theguardian.com/worldのウェブサイトを使用して最近のニュースを調べました。
    """
    tosay_fr = """
    J'ai consulté les dernières nouvelles sur le site https://www.theguardian.com/world
    """
    spk = Speech(enable=True, language="zh", voice_idx=0)
    for i in range(0, 2):
        print(f"Speaking chinese with voice {i}")
        spk.speak(tosay_zh, voice_idx=i)
    spk = Speech(enable=True, language="en", voice_idx=2)
    for i in range(0, 5):
        print(f"Speaking english with voice {i}")
        spk.speak(tosay_en, voice_idx=i)

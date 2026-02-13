import os, sys
import stat
import mimetypes
import configparser

if __name__ == "__main__": # if running as a script for individual testing
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sources.tools.tools import Tools

class FileFinder(Tools):
    """
    A tool that finds files in the current directory and returns their information.
    """
    def __init__(self):
        super().__init__()
        self.tag = "file_finder"
        self.name = "File Finder"
        self.description = "Finds files in the current directory and returns their information."
    
    def read_file(self, file_path: str) -> str:
        """
        Reads the content of a file.
        Args:
            file_path (str): The path to the file to read
        Returns:
            str: The content of the file
        """
        try:
            with open(file_path, 'r') as file:
                return file.read()
        except Exception as e:
            return f"Error reading file: {e}"
        
    def read_arbitrary_file(self, file_path: str, file_type: str) -> str:
        """
        Reads the content of a file with arbitrary encoding.
        Args:
            file_path (str): The path to the file to read
        Returns:
            str: The content of the file in markdown format
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            if mime_type.startswith(('image/', 'video/', 'audio/')):
                return "can't read file type: image, video, or audio files are not supported."
        content_raw = self.read_file(file_path)
        if "text" in file_type:
            content = content_raw
        elif "pdf" in file_type:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            content = '\n'.join([pt.extract_text() for pt in reader.pages])
        elif "binary" in file_type:
            content = content_raw.decode('utf-8', errors='replace')
        else:
            content = content_raw
        return content
    
    def get_file_info(self, file_path: str) -> str:
        """
        Gets information about a file, including its name, path, type, content, and permissions.
        Args:
            file_path (str): The path to the file
        Returns:
            str: A dictionary containing the file information
        """
        if os.path.exists(file_path):
            stats = os.stat(file_path)
            permissions = oct(stat.S_IMODE(stats.st_mode))
            file_type, _ = mimetypes.guess_type(file_path)
            file_type = file_type if file_type else "Unknown"
            content = self.read_arbitrary_file(file_path, file_type)
            
            result = {
                "filename": os.path.basename(file_path),
                "path": file_path,
                "type": file_type,
                "read": content,
                "permissions": permissions
            }
            return result
        else:
            return {"filename": file_path, "error": "File not found"}
    
    def recursive_search(self, directory_path: str, filename: str) -> str:
        """
        Recursively searches for files in a directory and its subdirectories.
        Args:
            directory_path (str): The directory to search in
            filename (str): The filename to search for
        Returns:
            str | None: The path to the file if found, None otherwise
        """
        file_path = None
        excluded_files = [".pyc", ".o", ".so", ".a", ".lib", ".dll", ".dylib", ".so", ".git"]
        for root, dirs, files in os.walk(directory_path):
            for f in files:
                if f is None:
                    continue
                if any(excluded_file in f for excluded_file in excluded_files):
                    continue
                if filename.strip() in f.strip():
                    file_path = os.path.join(root, f)
                    return file_path
        return None

    def optimized_recursive_search(self, directory_path: str, filenames: list[str]) -> dict[str, str]:
        """
        Recursively searches for multiple files in a directory and its subdirectories efficiently.
        Args:
            directory_path (str): The directory to search in
            filenames (list[str]): The list of filenames to search for
        Returns:
            dict[str, str]: A dictionary mapping filenames to their found paths
        """
        results = {}
        # Pre-strip filenames to avoid repeated stripping in loop
        pending_filenames = set(f.strip() for f in filenames)

        # Preserving existing exclusion logic from recursive_search (including strict substring check)
        excluded_files = [".pyc", ".o", ".so", ".a", ".lib", ".dll", ".dylib", ".git"]

        for root, dirs, files in os.walk(directory_path):
            if not pending_filenames:
                break

            for f in files:
                if f is None:
                    continue
                # Preserving original exclusion behavior
                if any(excluded_file in f for excluded_file in excluded_files):
                    continue

                f_stripped = f.strip()
                found_for_this_file = []
                for query in pending_filenames:
                    # Preserving original substring match behavior: query in filename
                    if query in f_stripped:
                        # Map the query back to the result.
                        # Note: we stored stripped queries in pending_filenames.
                        # The caller expects results keyed by the original filename?
                        # Wait, if I strip here, I lose the original string if it had whitespace.
                        # But original code did `filename.strip() in f.strip()`.
                        # So the key in the result should probably be the stripped version
                        # OR I need to maintain a mapping.
                        # However, `execute` uses `filename` (from block) to lookup.
                        # So I should probably keep `pending_filenames` as `(original, stripped)` or just iterate.
                        results[query] = os.path.join(root, f)
                        found_for_this_file.append(query)

                # Remove found queries from pending
                for found in found_for_this_file:
                    pending_filenames.remove(found)

                if not pending_filenames:
                    break
        
        return results

    def execute(self, blocks: list, safety:bool = False) -> str:
        """
        Executes the file finding operation for given filenames.
        Args:
            blocks (list): List of filenames to search for
        Returns:
            str: Results of the file search
        """
        if not blocks or not isinstance(blocks, list):
            return "Error: No valid filenames provided"

        # First pass: Collect all filenames and parse blocks
        parsed_blocks = []
        filenames_to_search = set()

        for block in blocks:
            filename = self.get_parameter_value(block, "name")
            action = self.get_parameter_value(block, "action")

            if filename is None:
                # If we return immediately, we might miss other valid blocks or disrupt flow.
                # But original code returned immediately on first error.
                return "Error: No filename provided\n"

            if action is None:
                action = "info"

            parsed_blocks.append({"filename": filename, "action": action})
            filenames_to_search.add(filename)

        print("File finder: optimized recursive search started...")
        # We pass the list of original filenames.
        # The optimized search will use stripped versions for matching,
        # but needs to return results keyed by SOMETHING that execute can use.
        # If I change optimized_search to use stripped keys, I must use stripped keys here too.

        search_results = self.optimized_recursive_search(self.work_dir, list(filenames_to_search))

        output = ""
        for block_data in parsed_blocks:
            filename = block_data["filename"]
            action = block_data["action"]

            # Since optimized_recursive_search now keys by stripped filename (based on my proposed change above),
            # I should lookup by stripped filename.
            # Wait, let's adjust optimized_recursive_search to handle this mapping correctly.

            file_path = search_results.get(filename.strip())

            if file_path is None:
                output += f"File: {filename} - not found\n"
                continue

            result = self.get_file_info(file_path)
            if "error" in result:
                output += f"File: {result['filename']} - {result['error']}\n"
            else:
                if action == "read":
                    output += "Content:\n" + result['read'] + "\n"
                else:
                    output += (f"File: {result['filename']}, "
                              f"found at {result['path']}, "
                              f"File type {result['type']}\n")
        return output.strip()

    def execution_failure_check(self, output: str) -> bool:
        """
        Checks if the file finding operation failed.
        Args:
            output (str): The output string from execute()
        Returns:
            bool: True if execution failed, False if successful
        """
        if not output:
            return True
        if "Error" in output or "not found" in output:
            return True
        return False

    def interpreter_feedback(self, output: str) -> str:
        """
        Provides feedback about the file finding operation.
        Args:
            output (str): The output string from execute()
        Returns:
            str: Feedback message for the AI
        """
        if not output:
            return "No output generated from file finder tool"
        
        feedback = "File Finder Results:\n"
        
        if "Error" in output or "not found" in output:
            feedback += f"Failed to process: {output}\n"
        else:
            feedback += f"Successfully found: {output}\n"
        return feedback.strip()

if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    tool = FileFinder()
    result = tool.execute(["""
action=read
name=tools.py
"""], False)
    print("Execution result:")
    print(result)
    print("\nFailure check:", tool.execution_failure_check(result))
    print("\nFeedback:")
    print(tool.interpreter_feedback(result))
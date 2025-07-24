from pathlib import Path
from typing import Dict


def load_prompts(directory: str) -> Dict[str, any]:
    """Load all .pmpt files from a directory and subdirectories recursively.

    Args:
        directory: Path to directory containing .pmpt files

    Returns:
        Dict mapping directory structure to prompt content, with filenames converted to UPPER_CASE
    """
    prompts = {}
    prompt_dir = Path(directory)

    def _load_prompts_recursive(current_dir: Path, base_dir: Path) -> Dict[str, any]:
        result = {}
        
        # Load .pmpt files in current directory
        for prompt_file in current_dir.glob("*.pmpt"):
            prompt_name = prompt_file.stem.upper()
            with open(prompt_file, "r") as f:
                result[prompt_name] = f.read().strip()
        
        # Recursively load subdirectories
        for subdir in current_dir.iterdir():
            if subdir.is_dir():
                subdir_name = subdir.name
                result[subdir_name] = _load_prompts_recursive(subdir, base_dir)
        
        return result

    return _load_prompts_recursive(prompt_dir, prompt_dir)
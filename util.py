from pathlib import Path
from typing import Dict


def load_prompts(directory: str) -> Dict[str, str]:
    """Load all .pmpt files from a directory and return as dict.

    Args:
        directory: Path to directory containing .pmpt files

    Returns:
        Dict mapping filename (without extension) to prompt content
    """
    prompts = {}
    prompt_dir = Path(directory)

    for prompt_file in prompt_dir.glob("*.pmpt"):
        prompt_name = prompt_file.stem
        with open(prompt_file, "r") as f:
            prompts[prompt_name] = f.read().strip()

    return prompts
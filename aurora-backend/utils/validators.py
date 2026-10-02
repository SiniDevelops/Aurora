import os
import re
from typing import List

def validate_vault_path(path: str) -> str:
    normalized = os.path.normpath(os.path.abspath(path))
    if not os.path.exists(normalized):
        raise ValueError(f"Path does not exist: {normalized}")
    if not os.path.isdir(normalized):
        raise ValueError(f"Path is not a directory: {normalized}")
    return normalized

def validate_note_path(path: str, vault_root: str) -> str:
    normalized_path = os.path.normpath(os.path.abspath(path))
    normalized_root = os.path.normpath(os.path.abspath(vault_root))
    
    if not normalized_path.startswith(normalized_root):
        raise ValueError(f"Path traversal attempt or path outside vault: {normalized_path}")
    return normalized_path

def validate_message_content(content: str, max_length: int = 10000) -> str:
    stripped = content.strip()
    if len(stripped) > max_length:
        raise ValueError(f"Message content exceeds maximum length of {max_length}")
    if not stripped:
        raise ValueError("Message content cannot be empty")
    return stripped

def sanitize_filename(name: str) -> str:
    # Remove invalid characters for Windows/Linux/Mac
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '', name)
    return sanitized.strip()

def is_markdown_file(path: str) -> bool:
    return path.lower().endswith('.md')

def is_excluded_path(path: str, excluded_folders: List[str]) -> bool:
    normalized = os.path.normpath(path)
    for folder in excluded_folders:
        if f"{os.sep}{folder}{os.sep}" in normalized or normalized.endswith(f"{os.sep}{folder}"):
            return True
    return False

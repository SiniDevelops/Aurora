"""
Safe line-level YAML editor.
Edits specific key:value pairs in aurora.yaml without destroying
comments, formatting, or unrelated sections.
"""

import re
import shutil
from pathlib import Path
from typing import Any


def _yaml_serialize_value(value: Any) -> str:
    """Serialize a Python value to inline YAML."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        items = ", ".join(_yaml_serialize_value(v) for v in value)
        return f"[{items}]"
    if isinstance(value, str):
        # Quote strings that could be misinterpreted
        if value in ("true", "false", "null", "yes", "no", "on", "off", ""):
            return f'"{value}"'
        if re.search(r'[:{}\[\],&*?|>!%@`#]', value):
            return f'"{value}"'
        return f'"{value}"'
    return str(value)


def edit_yaml_value(
    file_path: str,
    key_path: list[str],
    new_value: Any,
    backup: bool = True,
) -> bool:
    """
    Edit a specific key in a YAML file by finding the line and replacing the value.
    
    key_path: list of nested keys, e.g. ["llm", "active_provider"]
    new_value: the new value to set
    backup: create a .bak file before writing
    
    Returns True if the key was found and updated.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")

    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

    if backup:
        shutil.copy2(file_path, f"{file_path}.bak")

    # Walk the lines to find the target key at the right indentation level.
    # For key_path ["skills", "builtin", "linker", "enabled"]:
    #   - Find "skills:" at indent 0
    #   - Then "builtin:" at indent 2
    #   - Then "linker:" at indent 4
    #   - Then "enabled:" at indent 6  → replace value
    target_depth = 0
    found_ancestors = 0
    target_line_idx = -1

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(stripped)

        # If we haven't found all ancestors yet
        if found_ancestors < len(key_path) - 1:
            expected_key = key_path[found_ancestors]
            if stripped.startswith(f"{expected_key}:") and indent == target_depth:
                found_ancestors += 1
                target_depth = indent + 2  # YAML standard indent
                continue
            # Reset if we've gone past the section
            if indent <= (target_depth - 2) and found_ancestors > 0:
                # We've left the current section without finding our next ancestor.
                # For a tolerant approach, allow slight indent variations.
                pass
        else:
            # Looking for the final key
            final_key = key_path[-1]
            if stripped.startswith(f"{final_key}:") and indent >= target_depth - 2:
                target_line_idx = i
                break

    if target_line_idx < 0:
        return False

    # Replace just the value part on that line
    old_line = lines[target_line_idx]
    key_part = key_path[-1]
    # Match: <indent><key>:<optional space><old_value><optional comment>
    pattern = rf'^(\s*{re.escape(key_part)}:\s*)(.*?)(\s*#.*)?$'
    match = re.match(pattern, old_line.rstrip('\n\r'))
    if not match:
        return False

    prefix = match.group(1)
    comment = match.group(3) or ""
    new_line = f"{prefix}{_yaml_serialize_value(new_value)}{comment}\n"
    lines[target_line_idx] = new_line

    path.write_text("".join(lines), encoding="utf-8")
    return True

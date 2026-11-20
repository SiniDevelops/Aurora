"""
Safe line-level YAML editor.
Edits specific key:value pairs in aurora.yaml without destroying
comments, formatting, or unrelated sections.
"""

import re
import shutil
from pathlib import Path
from typing import Any

import yaml


def _yaml_serialize_scalar(value: Any) -> str:
    """Serialize a scalar Python value to valid inline YAML."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return str(value)


def _yaml_serialize_value(value: Any) -> str:
    """Serialize a Python value (scalar or inline list) to valid YAML."""
    if isinstance(value, list):
        items = ", ".join(_yaml_serialize_scalar(v) for v in value)
        return f"[{items}]"
    return _yaml_serialize_scalar(value)


def _find_key_line(lines: list[str], key_path: list[str]) -> tuple[int, int]:
    """
    Locate the line index and indentation of a nested YAML key.

    Maintains a stack of (indent, key) for active mapping ancestors so keys
    with identical names in different sections never collide.
    Returns (line_idx, indent) or (-1, -1) if not found.
    """
    stack: list[tuple[int, str]] = []
    key_re = re.compile(r"^([A-Za-z0-9_.-]+)\s*:(?:\s|$)")

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(stripped)

        # Sequence item ("- foo"): pop any mappings deeper than this list,
        # but don't push the list item as a mapping key.
        if stripped.startswith("- ") or stripped == "-":
            while stack and stack[-1][0] > indent:
                stack.pop()
            continue

        m = key_re.match(stripped)
        if not m:
            continue

        key = m.group(1)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        stack.append((indent, key))

        if [k for _, k in stack] == key_path:
            return i, indent

    return -1, -1


def edit_yaml_value(
    file_path: str,
    key_path: list[str],
    new_value: Any,
    backup: bool = True,
) -> bool:
    """
    Edit a specific key in a YAML file by finding the line and replacing its value.

    Handles both inline scalars/lists and multiline block lists (e.g.
    `enabled_categories:\n  - email\n  - phone`), and validates the resulting
    YAML before committing the write.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")

    original_text = path.read_text(encoding="utf-8")
    lines = original_text.splitlines(keepends=True)

    target_idx, target_indent = _find_key_line(lines, key_path)
    if target_idx < 0:
        return False

    old_line = lines[target_idx]
    key_part = key_path[-1]
    pattern = rf"^(\s*{re.escape(key_part)}:\s*)(.*?)(\s*#.*)?$"
    match = re.match(pattern, old_line.rstrip("\r\n"))
    if not match:
        return False

    prefix = match.group(1)
    old_val = match.group(2).strip()
    comment = match.group(3) or ""

    # Determine if there are multiline block list items directly beneath this key
    block_end = target_idx + 1
    if not old_val:
        while block_end < len(lines):
            nxt = lines[block_end]
            nxt_stripped = nxt.lstrip()
            if not nxt_stripped or nxt_stripped.startswith("#"):
                # Stop before trailing blank lines/comments so formatting stays intact
                break
            nxt_indent = len(nxt) - len(nxt_stripped)
            if nxt_indent > target_indent and (nxt_stripped.startswith("- ") or nxt_stripped == "-"):
                block_end += 1
            else:
                break

    if isinstance(new_value, list):
        if len(new_value) == 0:
            replacement = [f"{prefix.rstrip()} []{comment}\n"]
        elif block_end > target_idx + 1:
            # Preserve block-list style when the original was a block list
            item_indent = " " * (target_indent + 2)
            header = f"{prefix.rstrip()}{comment}\n"
            items = [f"{item_indent}- {v}\n" if isinstance(v, str) and re.fullmatch(r"[A-Za-z0-9_.-]+", v)
                     else f"{item_indent}- {_yaml_serialize_scalar(v)}\n"
                     for v in new_value]
            replacement = [header, *items]
        else:
            sep = "" if prefix.endswith(" ") else " "
            replacement = [f"{prefix}{sep}{_yaml_serialize_value(new_value)}{comment}\n"]
    else:
        sep = "" if prefix.endswith(" ") else " "
        replacement = [f"{prefix}{sep}{_yaml_serialize_value(new_value)}{comment}\n"]

    new_lines = lines[:target_idx] + replacement + lines[block_end:]
    new_text = "".join(new_lines)

    # Safety check: never write invalid YAML
    yaml.safe_load(new_text)

    if backup:
        shutil.copy2(file_path, f"{file_path}.bak")

    path.write_text(new_text, encoding="utf-8")
    return True

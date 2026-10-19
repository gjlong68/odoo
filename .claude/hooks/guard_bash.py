#!/usr/bin/env python3
"""PreToolUse guard: block destructive shell commands in the Odoo workspace."""

from __future__ import annotations

import json
import os
import re
import sys


def deny(reason: str) -> int:
    print(
        f"已阻止：{reason}\n"
        "该操作可能破坏 Odoo 源码、数据库或版本历史。请手动执行，"
        "或在明确知情时设置 ODOO_ALLOW_DESTRUCTIVE=1 后重试。",
        file=sys.stderr,
    )
    return 2


def is_recursive_force_rm(command: str) -> bool:
    # Inspect each command segment separately so that unrelated paths elsewhere
    # in the same shell command do not trigger a false positive.
    for segment in re.split(r"(?:&&|\|\||;|\n|\|)", command):
        tokens = segment.strip().split()
        rm_index = next(
            (index for index, token in enumerate(tokens) if token == "rm" or token.endswith("/rm")),
            None,
        )
        if rm_index is None:
            continue
        rm_tokens = tokens[rm_index:]
        options = [token for token in rm_tokens if token.startswith("-")]
        recursive = any(
            token == "--recursive" or re.fullmatch(r"-[a-zA-Z]*r[a-zA-Z]*", token) for token in options
        )
        force = any(token == "--force" or re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", token) for token in options)
        if not (recursive and force):
            continue
        targets = [
            token
            for token in rm_tokens
            if not token.startswith("-") and token != "rm" and not token.endswith("/rm")
        ]
        if not targets:
            return True
        dangerous_markers = {"/", ".", "..", "~", "$HOME", "*", "/opt/odoo20", "/opt/odoo20/"}
        if any(
            target in dangerous_markers or "odoo" in target.lower() or target.startswith("/opt/odoo20")
            for target in targets
        ):
            return True
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    if os.environ.get("ODOO_ALLOW_DESTRUCTIVE") == "1":
        return 0

    command = ((payload.get("tool_input") or {}).get("command") or "").strip()
    if not command:
        return 0
    # Help output is read-only and is needed to inspect CLI options.
    if re.search(r"(^|\s)(--help|-h)(\s|$)", command):
        return 0

    if is_recursive_force_rm(command):
        return deny("检测到递归强制删除（rm -rf），目标包含项目、核心或通配路径。")
    if re.search(r"\bdropdb\b", command):
        return deny("检测到 dropdb。")
    if re.search(r"\bdrop\s+database\b", command, re.IGNORECASE):
        return deny("检测到 DROP DATABASE。")
    if re.search(r"odoo-bin\b.*\bdb\b.*\b(drop|load|rename)\b", command):
        return deny("检测到 odoo-bin db drop/load/rename。")
    if re.search(r"odoo-bin\b.*\bdb\b.*\bduplicate\b", command) and re.search(
        r"(^|\s)(-f|--force)(\s|$)", command
    ):
        return deny("检测到 odoo-bin db duplicate -f（会先删除目标库）。")
    if re.search(r"\bgit\s+reset\s+--hard\b", command):
        return deny("检测到 git reset --hard。")
    if re.search(r"\bgit\s+clean\s+-[a-zA-Z]*f", command):
        return deny("检测到 git clean -f。")
    if re.search(r"\bgit\s+checkout\s+--\s", command):
        return deny("检测到 git checkout --（会丢弃工作区修改）。")
    if re.search(r"(^|\s)(sudo|doas)(\s|$)", command):
        return deny("检测到 sudo/doas。")
    if re.search(r"\bchmod\s+(-[a-zA-Z]+\s+)*777\b", command):
        return deny("检测到 chmod 777。")
    if re.search(r"\bpg_restore\b.*\bGoody\b", command):
        return deny("检测到向 Goody 库执行 pg_restore。")
    if re.search(r"\bpsql\b", command) and re.search(r"\bGoody\b", command) and re.search(
        r"\b(drop|truncate)\b", command, re.IGNORECASE
    ):
        return deny("检测到对 Goody 库执行 DROP/TRUNCATE。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

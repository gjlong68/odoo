#!/usr/bin/env python3
"""PreToolUse guard: keep upstream Odoo code, config and the venv read-only."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def deny(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    if payload.get("tool_name") not in EDIT_TOOLS:
        return 0

    tool_input = payload.get("tool_input") or {}
    raw_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not raw_path:
        return 0

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = root / path
    path = path.resolve()

    core = (root / "odoo").resolve()
    if path == core or core in path.parents:
        if os.environ.get("ODOO_ALLOW_CORE_EDIT") == "1":
            return 0
        return deny(
            f"已阻止：{path} 属于 Odoo 上游核心/企业源码（odoo/addons）。\n"
            "请在 custom/ 中新建模块，通过 _inherit、视图 xpath 或 assets 扩展实现。\n"
            "如确需临时修改核心，请显式设置 ODOO_ALLOW_CORE_EDIT=1 后重试。"
        )

    protected = (
        (root / "odoo20.conf").resolve(),
        (root / "odoo-venv").resolve(),
        Path("/etc/odoo20.conf").resolve(),
    )
    for item in protected:
        if path == item or item in path.parents:
            return deny(
                f"已阻止：{path} 是本地配置或运行环境，不允许由 AI 修改。\n"
                "如需调整开发配置，请修改 odoo20.conf.example 并手动同步真实配置。"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

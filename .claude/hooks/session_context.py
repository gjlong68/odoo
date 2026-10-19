#!/usr/bin/env python3
"""SessionStart hook: inject a short Odoo 20 workspace context."""

from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def read_version() -> str:
    release = ROOT / "odoo" / "release.py"
    if release.is_file():
        source = release.read_text(encoding="utf-8", errors="ignore")
        base = re.search(r"version_info\s*=\s*\((\d+),\s*(\d+)", source)
        suffix = re.search(r"version\s*\+=\s*['\"]([^'\"]+)['\"]", source)
        if base and suffix:
            return f"{base.group(1)}.{base.group(2)}{suffix.group(1)}"
        match = re.search(r"version\s*=\s*['\"]([^'\"]+)['\"]", source)
        if match:
            return match.group(1)
    pkg_info = ROOT / "PKG-INFO"
    if pkg_info.is_file():
        for line in pkg_info.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    return "20.0"


def main() -> int:
    modules = sorted(path.parent.name for path in (ROOT / "custom").glob("*/__manifest__.py"))
    module_text = ", ".join(modules) if modules else "无"
    print("[Odoo 20 开发上下文]")
    print(f"版本: {read_version()} | 默认数据库: Goody | custom 模块: {module_text}")
    print("硬规则: 不修改 odoo/ 核心；定制放 custom/；安全文件 security/ir.access.csv；")
    print("        视图用 <list> 和表达式属性；约束用 models.Constraint；控制器用 type=\"jsonrpc\"。")
    print("命令: make env | make run | make new-module MODULE=x | make test MODULE=x")
    print("Claude 命令: /new-module /check-module /update-module /test-module /review-custom /i18n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

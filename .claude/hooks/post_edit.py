#!/usr/bin/env python3
"""PostToolUse hook: validate edited files against Odoo 20 rules."""

from __future__ import annotations

import ast
import csv
import json
import os
import re
import sys
from pathlib import Path

try:
    from lxml import etree
except ImportError:  # pragma: no cover - lxml is part of the Odoo venv
    etree = None

EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
VERSION_RE = re.compile(r"^20\.0\.\d+\.\d+\.\d+$")
MODEL_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
XMLID_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
ACCESS_HEADER = ["id", "name", "model_id", "group_id/id", "operation", "domain"]
ALLOWED_LICENSES = {
    "GPL-2",
    "GPL-2 or any later version",
    "GPL-3",
    "GPL-3 or any later version",
    "AGPL-3",
    "LGPL-3",
    "Other OSI approved licence",
    "OEEL-1",
    "OPL-1",
    "Other proprietary",
}
DEPRECATED_PY = (
    (re.compile(r"\b_sql_constraints\s*="), "Odoo 20 使用 models.Constraint，不支持 _sql_constraints", "error"),
    (re.compile(r"\bdef\s+name_get\s*\("), "Odoo 20 使用 _compute_display_name，不支持 name_get", "error"),
    (re.compile(r"_rec_names_search\s*=\s*\["), "_rec_names_search 必须是 tuple，例如 ('name',)", "error"),
    (re.compile(r"@api\.(multi|one)\b"), "@api.multi / @api.one 已移除", "error"),
    (re.compile(r"type\s*=\s*['\"]json['\"]"), "控制器应使用 type='jsonrpc'", "error"),
    (re.compile(r"\bgroups_id\b"), "Odoo 20 使用 group_ids / user_ids，请确认字段名", "warn"),
    (re.compile(r"\bprint\s*\("), "模块代码不要使用 print，改用 logging", "warn"),
    (re.compile(r"\.cr\.commit\s*\("), "模块代码不要手动 commit", "warn"),
)


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def check_python(path: Path, report: Report, scan_conventions: bool) -> None:
    try:
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        report.error(f"{path}:{exc.lineno}: Python 语法错误: {exc.msg}")
        return
    if not scan_conventions:
        return
    for pattern, message, severity in DEPRECATED_PY:
        for match in pattern.finditer(source):
            line = source.count("\n", 0, match.start()) + 1
            text = f"{path}:{line}: {message}"
            if severity == "warn":
                report.warn(text)
            else:
                report.error(text)


def check_manifest(path: Path, report: Report) -> None:
    try:
        manifest = ast.literal_eval(path.read_text(encoding="utf-8"))
    except (SyntaxError, ValueError) as exc:
        report.error(f"{path}: __manifest__.py 无法解析: {exc}")
        return
    if not isinstance(manifest, dict):
        report.error(f"{path}: __manifest__.py 必须是字典")
        return
    version = str(manifest.get("version", ""))
    if not VERSION_RE.match(version):
        report.error(f"{path}: version {version!r} 不符合 20.0.x.y.z")
    license_name = manifest.get("license")
    if license_name is None:
        report.warn(f"{path}: 未声明 license，专有模块建议使用 OPL-1")
    elif license_name not in ALLOWED_LICENSES:
        report.error(f"{path}: license {license_name!r} 不合法")
    depends = manifest.get("depends")
    if not isinstance(depends, list) or not all(isinstance(item, str) for item in depends):
        report.error(f"{path}: depends 必须是模块名列表")
    data = manifest.get("data", [])
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        report.error(f"{path}: data 必须是文件路径列表")


def check_xml(path: Path, report: Report) -> None:
    if etree is None:
        report.warn(f"{path}: 缺少 lxml，跳过 XML 校验")
        return
    try:
        tree = etree.parse(str(path))
    except etree.XMLSyntaxError as exc:
        report.error(f"{path}: XML 语法错误: {exc}")
        return
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return
    if re.search(r"<tree\b", source):
        report.error(f"{path}: <tree> 已废弃，请使用 <list>")
    if "static" not in path.parts:
        for attr in ("attrs", "states"):
            for match in re.finditer(rf"\b{attr}\s*=", source):
                line = source.count("\n", 0, match.start()) + 1
                report.error(f"{path}:{line}: {attr}= 已废弃，请使用表达式属性")
        if re.search(r"""model\s*=\s*["']ir\.rule["']""", source):
            report.error(f'{path}: ir.rule 已移除，请使用 model="ir.access" + domain')
        if re.search(r"""model\s*=\s*["']ir\.model\.access["']""", source):
            report.error(f'{path}: ir.model.access 已移除，请使用 ir.access')
        if tree.getroot().tag != "odoo":
            report.warn(f"{path}: 根元素是 <{tree.getroot().tag}>，建议使用 <odoo>")


def check_access_csv(path: Path, report: Report) -> None:
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
    except OSError as exc:
        report.error(f"{path}: 无法读取: {exc}")
        return
    if not rows or rows[0] != ACCESS_HEADER:
        report.error(f"{path}: 表头必须为 {','.join(ACCESS_HEADER)}")
        return
    for number, row in enumerate(rows[1:], start=2):
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) != len(ACCESS_HEADER):
            report.error(f"{path}:{number}: 需要 {len(ACCESS_HEADER)} 列，实际 {len(row)} 列")
            continue
        record_id, name, model_id, group_id, operation, domain = [cell.strip() for cell in row]
        if not record_id or not name:
            report.error(f"{path}:{number}: id/name 不能为空")
        if not MODEL_RE.match(model_id):
            report.error(f"{path}:{number}: model_id 应为 module.model，实际 {model_id!r}")
        if group_id and not XMLID_RE.match(group_id):
            report.error(f"{path}:{number}: group_id/id 应为 module.group_xmlid，实际 {group_id!r}")
        if not operation or set(operation) - set("crud"):
            report.error(f"{path}:{number}: operation 只能是 c/r/u/d 的组合")


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
    if root not in path.parents:
        return 0
    if not path.is_file():
        return 0
    if path.suffix == ".ipynb":
        return 0

    report = Report()
    relative_parts = path.relative_to(root).parts
    scan_conventions = path.suffix == ".py" and not (
        {"scripts", ".claude"} & set(relative_parts)
    )
    if path.name == "__manifest__.py":
        check_manifest(path, report)
    elif path.suffix == ".py":
        check_python(path, report, scan_conventions)
    elif path.suffix == ".xml":
        check_xml(path, report)
    elif path.name == "ir.model.access.csv":
        report.error(f"{path}: 文件名已过时，请使用 security/ir.access.csv")
    elif path.name == "ir.access.csv":
        check_access_csv(path, report)

    for message in report.warnings:
        print(f"[WARN] {message}", file=sys.stderr)
    if report.errors:
        for message in report.errors:
            print(f"[ERROR] {message}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

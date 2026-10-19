#!/usr/bin/env python3
"""Static checks for an Odoo 20 custom module.

Exit code 0: no errors (warnings are allowed).
Exit code 1: at least one error.
"""

from __future__ import annotations

import argparse
import ast
import csv
import re
import sys
from pathlib import Path

try:
    from lxml import etree
except ImportError:  # pragma: no cover - lxml is part of the Odoo venv
    etree = None

ROOT = Path(__file__).resolve().parent.parent
ADDON_DIRS = ("custom", "oca", "app3", "web")
CORE_ADDONS = ROOT / "odoo" / "addons"
NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
MODEL_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
XMLID_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
VERSION_RE = re.compile(r"^20\.0\.\d+\.\d+\.\d+$")
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
ACCESS_HEADER = ["id", "name", "model_id", "group_id/id", "operation", "domain"]
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


class Checker:
    def __init__(self, module: Path) -> None:
        self.module = module
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def relative(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.module))
        except ValueError:
            return str(path)

    def run(self) -> None:
        print(f"模块: {self.module}")
        if not NAME_RE.match(self.module.name):
            self.error(f"目录名 {self.module.name!r} 不是合法的模块技术名")
        self.check_structure()
        manifest = self.check_manifest()
        self.check_python()
        self.check_xml()
        self.check_access_csv()
        if manifest is not None:
            self.check_data_files(manifest)

    def check_structure(self) -> None:
        if not (self.module / "__init__.py").is_file():
            self.error("缺少 __init__.py")
        tests = list((self.module / "tests").glob("test_*.py")) if (self.module / "tests").is_dir() else []
        if not tests:
            self.warn("没有 tests/test_*.py，建议补充 post_install 测试")

    def check_manifest(self) -> dict | None:
        path = self.module / "__manifest__.py"
        if not path.is_file():
            self.error("缺少 __manifest__.py")
            return None
        try:
            manifest = ast.literal_eval(path.read_text(encoding="utf-8"))
        except (SyntaxError, ValueError) as exc:
            self.error(f"__manifest__.py 无法解析: {exc}")
            return None
        if not isinstance(manifest, dict):
            self.error("__manifest__.py 必须是字典")
            return None

        for key in ("name", "version", "depends"):
            if key not in manifest:
                self.error(f"manifest 缺少必填键: {key}")
        version = str(manifest.get("version", ""))
        if not VERSION_RE.match(version):
            self.error(f"version {version!r} 不符合 Odoo 20 规范 20.0.x.y.z")
        license_name = manifest.get("license")
        if license_name is None:
            self.warn("manifest 未声明 license，专有模块建议使用 OPL-1")
        elif license_name not in ALLOWED_LICENSES:
            self.error(f"license {license_name!r} 不在 Odoo 允许的取值中")
        depends = manifest.get("depends")
        if not isinstance(depends, list) or not all(isinstance(d, str) for d in depends):
            self.error("manifest depends 必须是模块名列表")
        data = manifest.get("data", [])
        if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
            self.error("manifest data 必须是文件路径列表")
        return manifest

    def check_data_files(self, manifest: dict) -> None:
        data = manifest.get("data") or []
        if not isinstance(data, list):
            return
        security_indexes = [i for i, item in enumerate(data) if isinstance(item, str) and item.startswith("security/")]
        view_indexes = [i for i, item in enumerate(data) if isinstance(item, str) and item.startswith("views/")]
        if security_indexes and view_indexes and max(security_indexes) > min(view_indexes):
            self.warn("manifest data 中 security 文件应放在 views 之前")
        for item in data:
            if not isinstance(item, str):
                continue
            if not (self.module / item).is_file():
                self.error(f"manifest data 引用的文件不存在: {item}")

    def check_python(self) -> None:
        for path in self.module.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            relative = path.relative_to(self.module)
            try:
                source = path.read_text(encoding="utf-8")
                ast.parse(source, filename=str(path))
            except SyntaxError as exc:
                self.error(f"{relative}:{exc.lineno}: Python 语法错误: {exc.msg}")
                continue
            if "migrations" in relative.parts:
                continue
            for pattern, message, severity in DEPRECATED_PY:
                match = pattern.search(source)
                if match:
                    line = source.count("\n", 0, match.start()) + 1
                    level = self.warn if severity == "warn" else self.error
                    level(f"{relative}:{line}: {message}")

    def check_xml(self) -> None:
        if etree is None:
            self.error("缺少 lxml，无法校验 XML；请使用 odoo-venv/bin/python 运行")
            return
        for path in self.module.rglob("*.xml"):
            if "__pycache__" in path.parts:
                continue
            relative = path.relative_to(self.module)
            try:
                tree = etree.parse(str(path))
            except etree.XMLSyntaxError as exc:
                self.error(f"{relative}: XML 语法错误: {exc}")
                continue
            source = path.read_text(encoding="utf-8")
            if re.search(r"<tree\b", source):
                self.error(f"{relative}: <tree> 已废弃，请使用 <list>")
            if "static" not in relative.parts:
                for attr in ("attrs", "states"):
                    match = re.search(rf"\b{attr}\s*=", source)
                    if match:
                        line = source.count("\n", 0, match.start()) + 1
                        self.error(f"{relative}:{line}: {attr}= 已废弃，请使用表达式属性")
                if re.search(r"""model\s*=\s*["']ir\.rule["']""", source):
                    self.error(f"{relative}: ir.rule 已移除，请使用 model=\"ir.access\" + domain")
                if re.search(r"""model\s*=\s*["']ir\.model\.access["']""", source):
                    self.error(f"{relative}: ir.model.access 已移除，请使用 ir.access")
            root = tree.getroot()
            if root.tag != "odoo" and "static" not in relative.parts:
                self.warn(f"{relative}: 根元素是 <{root.tag}>，Odoo 20 建议使用 <odoo>")

    def check_access_csv(self) -> None:
        old = self.module / "security" / "ir.model.access.csv"
        if old.exists():
            self.error("security/ir.model.access.csv 已过时，请改用 security/ir.access.csv")
        path = self.module / "security" / "ir.access.csv"
        if not path.exists():
            return
        try:
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle))
        except OSError as exc:
            self.error(f"security/ir.access.csv 无法读取: {exc}")
            return
        if not rows:
            self.error("security/ir.access.csv 为空")
            return
        if rows[0] != ACCESS_HEADER:
            self.error(f"ir.access.csv 表头必须为: {','.join(ACCESS_HEADER)}")
            return
        for number, row in enumerate(rows[1:], start=2):
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) != len(ACCESS_HEADER):
                self.error(
                    f"ir.access.csv:{number}: 需要 {len(ACCESS_HEADER)} 列，实际 {len(row)} 列"
                    "（含逗号的 domain 需要加引号）"
                )
                continue
            record_id, name, model_id, group_id, operation, domain = [cell.strip() for cell in row]
            if not record_id or not name:
                self.error(f"ir.access.csv:{number}: id/name 不能为空")
            if not MODEL_RE.match(model_id):
                self.error(f"ir.access.csv:{number}: model_id 应为 module.model，实际 {model_id!r}")
            if group_id and not XMLID_RE.match(group_id):
                self.error(f"ir.access.csv:{number}: group_id/id 应为 module.group_xmlid，实际 {group_id!r}")
            if not operation or set(operation) - set("crud"):
                self.error(f"ir.access.csv:{number}: operation 只能是 c/r/u/d 的组合，实际 {operation!r}")
            if not group_id and not domain:
                self.warn(f"ir.access.csv:{number}: 没有 group_id 也没有 domain，可能是无效的 restriction")

    def report(self) -> int:
        for message in self.errors:
            print(f"[ERROR] {message}")
        for message in self.warnings:
            print(f"[WARN]  {message}")
        print(f"汇总: {len(self.errors)} error(s), {len(self.warnings)} warning(s)")
        return 1 if self.errors else 0


def find_module(value: str) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_dir():
        return candidate.resolve()
    candidate = ROOT / value
    if candidate.is_dir():
        return candidate.resolve()
    for base in ADDON_DIRS:
        candidate = ROOT / base / value
        if candidate.is_dir():
            return candidate.resolve()
    candidate = CORE_ADDONS / value
    if candidate.is_dir():
        return candidate.resolve()
    print(f"错误: 找不到模块 {value!r}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", help="module name or path")
    args = parser.parse_args()
    checker = Checker(find_module(args.module))
    checker.run()
    return checker.report()


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Create an Odoo 20 module skeleton following the project conventions."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE_ADDONS = ROOT / "odoo" / "addons"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
MODULE_VERSION = "20.0.1.0.0"
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="technical module name")
    parser.add_argument("--title", help="human readable module title")
    parser.add_argument("--depends", default="base", help="comma separated module dependencies")
    parser.add_argument("--kind", choices=("extension", "model"), default="extension")
    parser.add_argument("--entity", default="item", help="model entity name for --kind=model")
    parser.add_argument("--dest", default=str(ROOT / "custom"), help="directory that will contain the module")
    parser.add_argument("--license", default="OPL-1", dest="license_name")
    parser.add_argument("--author", default="Your Company")
    parser.add_argument("--website", default="")
    return parser.parse_args()


def fail(message: str) -> None:
    print(f"错误: {message}", file=sys.stderr)
    raise SystemExit(1)


def normalize_depends(raw: str) -> list[str]:
    depends: list[str] = []
    for item in raw.split(","):
        dep = item.strip()
        if not dep:
            continue
        if not NAME_RE.match(dep):
            fail(f"依赖模块名不合法: {dep!r}")
        if dep not in depends:
            depends.append(dep)
    if "base" not in depends:
        depends.insert(0, "base")
    return depends


def class_name(entity: str) -> str:
    return "".join(part.capitalize() for part in entity.split("_") if part)


def render(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def main() -> None:
    args = parse_args()
    name = args.name.strip()
    if not NAME_RE.match(name):
        fail("模块名必须匹配 ^[a-z][a-z0-9_]*$")
    if (CORE_ADDONS / name).exists():
        fail(f"模块名 {name} 与 odoo/addons 中的核心/企业模块冲突")

    entity = args.entity.strip()
    if not NAME_RE.match(entity):
        fail("--entity 必须匹配 ^[a-z][a-z0-9_]*$")
    if args.license_name not in ALLOWED_LICENSES:
        fail(f"license 不合法: {args.license_name!r}")

    depends = normalize_depends(args.depends)
    title = (args.title or name.replace("_", " ").title()).strip()
    if not title:
        fail("--title 不能为空")
    if any(char in title for char in "<>'\"&"):
        fail("TITLE 不能包含 < > ' \" & 等特殊字符")

    dest = Path(args.dest).expanduser().resolve()
    target = dest / name
    if target.exists():
        fail(f"目标目录已存在: {target}")

    template_dir = TEMPLATES_DIR / args.kind
    if not template_dir.is_dir():
        fail(f"模板目录不存在: {template_dir}")

    values = {
        "MODULE": name,
        "TITLE": title,
        "DEPENDS": repr(depends),
        "ENTITY": entity,
        "CLASS": class_name(entity),
        "VERSION": MODULE_VERSION,
        "YEAR": str(dt.date.today().year),
        "AUTHOR": args.author,
        "WEBSITE": args.website,
        "LICENSE": args.license_name,
    }

    created: list[Path] = []
    for source in sorted(template_dir.rglob("*")):
        if not source.is_file():
            continue
        relative = render(str(source.relative_to(template_dir)), values)
        if relative.endswith(".tmpl"):
            relative = relative[: -len(".tmpl")]
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(render(source.read_text(encoding="utf-8"), values), encoding="utf-8")
        created.append(destination)

    print(f"已创建模块 {name} ({args.kind}) -> {target}")
    for path in created:
        print(f"  {path.relative_to(target)}")
    print("\n下一步:")
    print(f"  make validate MODULE={name}")
    print(f"  make install MODULE={name}")
    print(f"  make test MODULE={name}")


if __name__ == "__main__":
    main()

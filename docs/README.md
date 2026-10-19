# Odoo 20 企业定制开发配置工程

本目录是 `/opt/odoo20` 工作区的 AI 辅助开发配置。目标是让 VS Code 与 Claude Code 在 Odoo 20 企业定制场景下开箱可用，同时把“不修改核心、不误删库、遵循 Odoo 20 API”变成可执行的护栏。

## 交付内容

| 路径 | 作用 |
|---|---|
| `CLAUDE.md` | Claude Code 项目指令：硬规则、Odoo 20 API 速查、命令和工作流 |
| `.claude/settings.json` | 权限、hooks、Claude Code 项目配置 |
| `.claude/hooks/` | 核心/配置写保护、危险命令拦截、编辑后校验、会话上下文 |
| `.claude/commands/` | `/new-module`、`/check-module`、`/update-module`、`/test-module`、`/review-custom`、`/i18n` |
| `.claude/agents/odoo-reviewer.md` | 只读模块审查子代理 |
| `.claude/skills/odoo-module-development/` | 模块开发 skill 与检查表 |
| `.vscode/settings.json` | 解释器、Pylance、Ruff、XML、`ODOO_RC` |
| `.vscode/extensions.json` | 推荐扩展 |
| `.vscode/launch.json` | 运行、测试、Shell 调试配置 |
| `.vscode/tasks.json` | 安装/升级/测试/校验/备份等任务 |
| `Makefile` | 统一命令入口 |
| `scripts/new_module.py` | 生成符合 Odoo 20 的模块骨架 |
| `scripts/check_module.py` | 静态校验模块 |
| `ruff.toml` | 只检查 `custom/`、`scripts/`、`.claude/hooks/` |
| `docs/` | 开发规范、工作流、企业定制规则、Claude Code 说明 |

## 5 分钟快速开始

```bash
cd /opt/odoo20

# 1. 安装开发工具（ruff）
make dev-setup

# 2. 检查环境
make env

# 3. 启动 Odoo（默认 Goody，--dev=xml）
make run

# 4. 新建并安装一个模块
make new-module MODULE=custom_demo TITLE="Demo" DEPENDS=base KIND=model
make validate MODULE=custom_demo
make install MODULE=custom_demo
make test MODULE=custom_demo
```

在 Claude Code 中：

```text
/new-module custom_demo account_accountant extension
/check-module custom_demo
/test-module custom_demo
/review-custom custom_demo
```

## 验证

```bash
# JSON / TOML / Python 语法
python3 -m json.tool .vscode/settings.json >/dev/null
python3 -m json.tool .vscode/extensions.json >/dev/null
python3 -m json.tool .vscode/launch.json >/dev/null
python3 -m json.tool .vscode/tasks.json >/dev/null
python3 -m json.tool .claude/settings.json >/dev/null
python3 -c "import tomllib; tomllib.load(open('ruff.toml','rb'))"

# Odoo 启动（不监听 HTTP）
odoo-venv/bin/python odoo-bin server -c odoo20.conf -d Goody --stop-after-init --no-http

# 模块全流程
make new-module MODULE=custom_demo TITLE="Demo" DEPENDS=base KIND=model
make validate MODULE=custom_demo
make install MODULE=custom_demo
make test MODULE=custom_demo
```

> 验证完成后可删除 `custom/custom_demo`，保持 `custom/` 干净。

## hooks 与覆盖开关

- 修改 `odoo/`、`odoo20.conf`、`odoo-venv/` 会被 `guard_paths.py` 阻止。
- `rm -rf` 项目/核心、`dropdb`、`db drop/load/rename`、`db duplicate -f`、`git reset --hard`、`git clean -f`、`sudo`、`chmod 777` 等会被 `guard_bash.py` 阻止。
- 编辑 `.py`/`.xml`/`ir.access.csv` 后会由 `post_edit.py` 检查 Odoo 20 废弃写法。
- 确需临时绕过：

```bash
ODOO_ALLOW_CORE_EDIT=1        # 允许修改 odoo/
ODOO_ALLOW_DESTRUCTIVE=1      # 允许危险 shell 命令
```

这些开关是给开发者的，不要让 AI 自行设置。hooks 是防误操作护栏，不是安全沙箱。

## 回滚 / 禁用

- 禁用某个 hook：从 `.claude/settings.json` 的 `hooks` 中删除对应条目。
- 完全禁用项目 hooks：删除或清空 `.claude/settings.json` 的 `hooks` 键。
- 恢复 VS Code 配置：`git checkout -- .vscode/`（首次提交后可用）。
- 真实配置 `odoo20.conf` 不在 Git 中；需要重建时复制 `odoo20.conf.example` 并替换 `admin_passwd`。

## Git

工作区已初始化 Git，只跟踪配置、文档、脚本和 `custom/` 模块；`odoo/`、`odoo-venv/`、`odoo20.conf`、`backups/`、`oca/` 被忽略。

```bash
git status --short
git check-ignore -v odoo/addons/base/__init__.py odoo-venv/bin/python odoo20.conf
```

## 相关文档

- [Odoo 20 开发规范](odoo20-development-standards.md)
- [开发工作流](development-workflow.md)
- [企业模块二次开发](enterprise-customization.md)
- [Claude Code 配置说明](claude-code-setup.md)

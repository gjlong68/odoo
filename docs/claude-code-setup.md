# Claude Code 配置说明

## 1. 配置文件

| 文件 | 作用 |
|---|---|
| `CLAUDE.md` | 项目级指令，每次会话加载 |
| `.claude/settings.json` | 权限、hooks |
| `.claude/settings.local.json` | 本机个人覆盖（不提交） |
| `.claude/commands/*.md` | 斜杠命令 |
| `.claude/agents/*.md` | 子代理 |
| `.claude/skills/<name>/SKILL.md` | 技能 |
| `.claude/hooks/*.py` | hook 脚本 |
| `.mcp.json` | 项目级 MCP（当前未启用） |

## 2. 权限

`.claude/settings.json` 的 `permissions`：

- `allow`：`make`、`odoo-bin`、项目脚本、`ruff`、常用只读 shell、对 `Goody`/`demo`/`Template` 的只读 `psql`。
- `deny`：读取 `odoo20.conf`/`/etc/odoo20.conf`；编辑 `odoo/`；`sudo`、`rm -rf`、`dropdb`、`db drop`、`git reset --hard`、`git clean`。
- `ask`：`git push`。

权限规则和 hooks 是两层防护：权限规则做静态匹配，hooks 做更细的路径/命令检查。新增允许项前，先确认不会绕过核心保护。

## 3. Hooks

### `guard_paths.py`（PreToolUse）

阻止对以下路径的 `Write`/`Edit`/`MultiEdit`/`NotebookEdit`：

- `odoo/`（上游核心/企业源码）
- `odoo20.conf`、`/etc/odoo20.conf`
- `odoo-venv/`

覆盖开关：`ODOO_ALLOW_CORE_EDIT=1`（只对 `odoo/` 生效；配置和 venv 仍禁止）。

### `guard_bash.py`（PreToolUse）

阻止：

- 对项目/核心/通配路径的 `rm -rf`
- `dropdb`、`DROP DATABASE`
- `odoo-bin db drop/load/rename`
- `odoo-bin db duplicate -f`
- `git reset --hard`、`git clean -f`、`git checkout --`
- `sudo`/`doas`、`chmod 777`
- 向 `Goody` 执行 `pg_restore`、`DROP/TRUNCATE`

`--help`/`-h` 只读命令不受影响。覆盖开关：`ODOO_ALLOW_DESTRUCTIVE=1`。

### `post_edit.py`（PostToolUse）

编辑后检查：

- Python：`ast.parse`；Odoo 20 废弃写法（`_sql_constraints`、`name_get`、`attrs`/`states`、`type="json"`、`ir.rule`、`ir.model.access` 等）。
- `__manifest__.py`：版本、license、depends、data。
- XML：语法、`<tree>`、`attrs`/`states`、旧安全模型。
- `security/ir.access.csv`：表头、列数、operation、model_id、group_id。

有 ERROR 时 hook 返回退出码 2，Claude 会收到错误并要求修正；WARN 只提示。

### `session_context.py`（SessionStart）

注入版本、默认数据库、`custom/` 模块列表和硬规则摘要。

## 4. 命令

| 命令 | 作用 |
|---|---|
| `/new-module <name> [depends] [extension\|model]` | 创建模块骨架 |
| `/check-module <name>` | 静态校验 |
| `/update-module <name> [db]` | 升级模块 |
| `/test-module <name> [db]` | 升级并测试 |
| `/review-custom <name>` | 只读审查 |
| `/i18n <name> [export\|import\|pot] [file.po]` | 翻译 |

命令是提示模板，最终仍受权限和 hooks 约束。

## 5. Agent 与 Skill

- `odoo-reviewer`：只读审查，工具仅 `Read, Grep, Glob`；输出 `severity | file:line | issue | fix`。
- `odoo-module-development`：在创建/扩展/修改/审查 Odoo 模块时自动触发；包含工作流、硬规则和检查表。

## 6. Provider / Model

本项目 `.claude/settings.json` **不设置** `env` 或 `model`。当前用户级 `~/.claude/settings.json` 通过 DeepSeek 的 Anthropic 兼容接口提供模型映射；切换 provider 时只改用户级配置，不要写进项目配置，避免影响其他工作区。

## 7. MCP（可选）

当前未配置 MCP。后续如需接入 PostgreSQL：

- 选择可信的 PostgreSQL MCP server，并固定版本。
- 使用只读数据库角色，只授予 `SELECT`。
- 不要把 `odoo20.conf`、`.env` 或管理员密码交给 MCP。
- 项目级配置写入 `.mcp.json`，按需在 `.claude/settings.local.json` 中批准；不要把密钥提交到 Git。

示例结构：

```json
{
  "mcpServers": {
    "postgres-readonly": {
      "type": "stdio",
      "command": "<trusted-mcp-binary>",
      "args": ["--readonly"],
      "env": {
        "PGDATABASE": "Goody"
      }
    }
  }
}
```

具体 command/args 取决于所选 MCP server；先阅读其文档并验证只读权限。

## 8. 故障排查

| 现象 | 检查 |
|---|---|
| 设置不生效 | `.claude/settings.json` 是否为合法 JSON；工作区是否已信任 |
| hooks 不触发 | 扩展是否需要重启；hook 命令路径是否存在；`/permissions` 查看规则 |
| 编辑核心没有被阻止 | hook 是否被禁用；`ODOO_ALLOW_CORE_EDIT` 是否被设置 |
| `post_edit` 误报 | 确认文件是否在 `custom/`；`static/` 下的 OWL XML 会跳过 `attrs` 检查 |
| 命令不出现 | `.claude/commands/*.md` 是否有合法 frontmatter；是否重启会话 |
| skill 不触发 | `SKILL.md` 的 `name` 是否与目录名一致；description 是否包含触发场景 |
| 子代理不可用 | `.claude/agents/odoo-reviewer.md` frontmatter 是否合法 |

## 9. 安全边界

- hooks 和权限规则用于减少误操作，不是操作系统级沙箱。
- 有权限的 shell 仍可执行未覆盖的危险命令；关键操作需人工确认。
- 不要把生产库凭据、`admin_passwd`、API token 写入项目配置或提交到 Git。
- 覆盖开关 `ODOO_ALLOW_CORE_EDIT`/`ODOO_ALLOW_DESTRUCTIVE` 只应在明确知情时临时使用。

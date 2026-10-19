SHELL := /bin/bash
CURDIR := $(shell pwd)
PY ?= $(CURDIR)/odoo-venv/bin/python
ODOO ?= $(PY) $(CURDIR)/odoo-bin
CONF ?= $(CURDIR)/odoo20.conf
DB ?= Goody
MODULE ?=
TITLE ?= $(MODULE)
DEPENDS ?= base
KIND ?= extension
ENTITY ?= item
LANG ?= zh_CN
FILE ?=

.PHONY: help env run run-dev install update test test-fast shell new-module validate check lint lint-fix i18n-export i18n-pot i18n-import backup duplicate list-modules dev-setup clean

help:
	@echo "Odoo 20 开发命令："
	@echo "  make env                              检查 Odoo/Python/数据库/自定义模块"
	@echo "  make run [DB=Goody]                   启动服务 (--dev=xml)"
	@echo "  make run-dev [DB=Goody]               启动服务 (--dev=all)"
	@echo "  make install MODULE=x [DB=Goody]      安装模块"
	@echo "  make update MODULE=x [DB=Goody]       升级模块"
	@echo "  make test MODULE=x [DB=Goody]         升级并运行模块测试"
	@echo "  make test-fast MODULE=x [DB=Goody]    不升级，直接运行模块测试"
	@echo "  make shell [DB=Goody]                 打开 Odoo shell"
	@echo "  make new-module MODULE=x [TITLE=..] [DEPENDS=base] [KIND=extension|model]"
	@echo "  make validate MODULE=x                静态校验模块"
	@echo "  make lint                             运行 Ruff"
	@echo "  make i18n-export MODULE=x [LANG=zh_CN] 导出翻译"
	@echo "  make i18n-pot MODULE=x                导出 .pot 模板"
	@echo "  make i18n-import MODULE=x FILE=xx.po  导入翻译"
	@echo "  make backup [DB=Goody]                备份数据库（含 filestore）"
	@echo "  make duplicate [DB=Goody]             复制为 <DB>_test 并 neutralize"
	@echo "  make list-modules                     列出 custom/ 下的模块"
	@echo "  make dev-setup                        安装开发工具 (ruff)"
	@echo "  make clean                            清理项目缓存"

env:
	@echo "== Odoo =="
	@$(ODOO) --version
	@echo "== Python =="
	@$(PY) -c "import sys; print(sys.version.split()[0])"
	@echo "== Database $(DB) =="
	@psql -d $(DB) -Atc "select 'db=' || current_database() || ', installed=' || count(*) from ir_module_module where state='installed';" 2>/dev/null || echo "无法连接数据库 $(DB)"
	@echo "== custom modules =="
	@find custom -mindepth 1 -maxdepth 2 -name __manifest__.py -printf '%h\n' 2>/dev/null | sed 's#^custom/##' | sort || true

run:
	$(ODOO) server -c $(CONF) -d $(DB) --dev=xml

run-dev:
	$(ODOO) server -c $(CONF) -d $(DB) --dev=all

install:
	@test -n "$(MODULE)" || { echo "用法: make install MODULE=<module> [DB=Goody]"; exit 1; }
	$(ODOO) module install -c $(CONF) -d $(DB) $(MODULE)

update:
	@test -n "$(MODULE)" || { echo "用法: make update MODULE=<module> [DB=Goody]"; exit 1; }
	$(ODOO) module upgrade -c $(CONF) -d $(DB) $(MODULE)

test:
	@test -n "$(MODULE)" || { echo "用法: make test MODULE=<module> [DB=Goody]"; exit 1; }
	$(ODOO) server -c $(CONF) -d $(DB) -u $(MODULE) --test-tags /$(MODULE) --stop-after-init --no-http

test-fast:
	@test -n "$(MODULE)" || { echo "用法: make test-fast MODULE=<module> [DB=Goody]"; exit 1; }
	$(ODOO) server -c $(CONF) -d $(DB) --test-tags /$(MODULE) --stop-after-init --no-http

shell:
	$(ODOO) shell -c $(CONF) -d $(DB)

new-module:
	@test -n "$(MODULE)" || { echo "用法: make new-module MODULE=<module> [TITLE=..] [DEPENDS=base] [KIND=extension|model]"; exit 1; }
	$(PY) scripts/new_module.py --name "$(MODULE)" --title "$(TITLE)" --depends "$(DEPENDS)" --kind "$(KIND)" --entity "$(ENTITY)" --dest "$(CURDIR)/custom"

validate:
	@test -n "$(MODULE)" || { echo "用法: make validate MODULE=<module>"; exit 1; }
	$(PY) scripts/check_module.py "$(MODULE)"

check: validate

lint:
	$(PY) -m ruff check custom scripts .claude/hooks

lint-fix:
	$(PY) -m ruff check --fix custom scripts .claude/hooks

i18n-export:
	@test -n "$(MODULE)" || { echo "用法: make i18n-export MODULE=<module> [LANG=zh_CN]"; exit 1; }
	$(ODOO) i18n export -c $(CONF) -d $(DB) -l $(LANG) $(MODULE)

i18n-pot:
	@test -n "$(MODULE)" || { echo "用法: make i18n-pot MODULE=<module>"; exit 1; }
	$(ODOO) i18n export -c $(CONF) -d $(DB) -l pot $(MODULE)

i18n-import:
	@test -n "$(MODULE)" || { echo "用法: make i18n-import MODULE=<module> FILE=<file.po> [LANG=zh_CN]"; exit 1; }
	@test -n "$(FILE)" || { echo "缺少 FILE=<file.po>"; exit 1; }
	$(ODOO) i18n import -c $(CONF) -d $(DB) -l $(LANG) -w $(FILE)

backup:
	@mkdir -p "$(CURDIR)/backups"
	$(ODOO) db -c $(CONF) dump $(DB) "$(CURDIR)/backups/$(DB)-$(shell date +%Y%m%d-%H%M%S).zip"

duplicate:
	$(ODOO) db -c $(CONF) duplicate $(DB) $(DB)_test -n

list-modules:
	@find custom -mindepth 1 -maxdepth 2 -name __manifest__.py -printf '%h\n' 2>/dev/null | sed 's#^custom/##' | sort || true

dev-setup:
	$(PY) -m pip install -r requirements-dev.txt

clean:
	@find custom scripts .claude -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .ruff_cache
	@echo "已清理项目缓存"

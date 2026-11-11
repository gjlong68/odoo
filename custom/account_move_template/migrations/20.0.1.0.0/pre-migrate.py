# Copyright 2026
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
"""Remove security xmlids tied to models removed in Odoo 20.

Odoo 20 replaced ``ir.model.access`` and ``ir.rule`` with ``ir.access``.
``security/ir.access.csv`` reuses the historical external ids, so any row
created by a previous (pre-20.0) release must be dropped before the new
records are loaded; otherwise ``_load_records`` raises a model mismatch.
"""

OBSOLETE_SECURITY_XMLIDS = (
    "access_account_move_template_user",
    "access_account_move_template_line_user",
    "access_account_move_template_run_user",
    "access_account_move_template_line_run_user",
    "account_move_template_comp_rule",
)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = 'account_move_template'
          AND name = ANY(%s)
          AND model IN ('ir.model.access', 'ir.rule')
        """,
        (list(OBSOLETE_SECURITY_XMLIDS),),
    )

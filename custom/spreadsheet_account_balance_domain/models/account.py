# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class AccountAccount(models.Model):
    _inherit = "account.account"

    def _validate_extra_domain(self, domain):
        """Validate and normalize the optional ODOO.BALANCE.TAG domain.

        Accepts None, an empty string/list, a JSON-encoded string, or an
        already-parsed list/tuple of conditions. Returns a list or None.

        Raises UserError on invalid input so that @spreadsheet_safe_batch can
        isolate the failing formula instead of failing the whole batch.
        """
        if isinstance(domain, str):
            if not domain.strip():
                return None
            try:
                domain = json.loads(domain)
            except json.JSONDecodeError as exc:
                raise UserError(_(
                    "The ODOO.BALANCE.TAG domain must be valid JSON, e.g. "
                    '[["debit", ">", 50]].'
                )) from exc

        if not domain:
            return None
        if not isinstance(domain, (list, tuple)):
            raise UserError(_(
                "The ODOO.BALANCE.TAG domain must be a list of "
                "[field, operator, value] conditions."
            ))

        try:
            Domain(domain).validate(self.env["account.move.line"].sudo())
        except (TypeError, ValueError) as exc:
            raise UserError(_(
                "Invalid ODOO.BALANCE.TAG domain: %s", exc
            )) from exc
        return list(domain)

    def _build_spreadsheet_formula_domain(self, formula_params, default_accounts=False):
        if "account_tag_ids" not in formula_params:
            return super()._build_spreadsheet_formula_domain(
                formula_params, default_accounts=default_accounts
            )

        company_id = formula_params.get("company_id") or self.env.company.id
        company = self.env["res.company"].browse(company_id)
        start, end = self._get_date_period_boundaries(formula_params["date_range"], company)

        # "21/12/2022" is an end date: balance up to that date. Quarter, month
        # and year formats are periods: only movements within the period.
        # The same rule applies to every account type.
        if formula_params["date_range"].get("range_type") == "day":
            period_domain = Domain([("date", "<=", end)])
        else:
            period_domain = Domain([("date", ">=", start), ("date", "<=", end)])

        tag_ids = [
            int(tag_id)
            for tag_id in formula_params.get("account_tag_ids", [])
            if tag_id
        ]
        account_domain = (
            Domain("account_id.tag_ids", "in", tag_ids) if tag_ids else Domain.FALSE
        )

        posted_domain = (
            [("move_id.state", "!=", "cancel")]
            if formula_params.get("include_unposted")
            else [("move_id.state", "=", "posted")]
        )

        domain = Domain.AND([
            account_domain,
            period_domain,
            [("company_id", "=", company_id)],
            posted_domain,
        ])

        partner_ids = [
            int(partner_id)
            for partner_id in formula_params.get("partner_ids", [])
            if partner_id
        ]
        if partner_ids:
            domain &= Domain("partner_id", "in", partner_ids)

        extra_domain = self._validate_extra_domain(formula_params.get("domain"))
        if extra_domain:
            domain = Domain.AND([domain, extra_domain])

        return domain

# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, api, models
from odoo.addons.spreadsheet.utils.helpers import spreadsheet_safe_batch
from odoo.exceptions import UserError
from odoo.fields import Domain


class AccountAccount(models.Model):
    _inherit = "account.account"

    def _validate_extra_domain(self, domain):
        """Validate and normalize the optional spreadsheet formula domain.

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
                    "The spreadsheet domain must be valid JSON, e.g. "
                    '[["debit", ">", 50]].'
                )) from exc

        if not domain:
            return None
        if not isinstance(domain, (list, tuple)):
            raise UserError(_(
                "The spreadsheet domain must be a list of "
                "[field, operator, value] conditions."
            ))

        try:
            Domain(domain).validate(self.env["account.move.line"].sudo())
        except (TypeError, ValueError) as exc:
            raise UserError(_(
                "Invalid spreadsheet domain: %s", exc
            )) from exc
        return list(domain)

    @api.model
    @spreadsheet_safe_batch
    def spreadsheet_fetch_balance_tag(self, args_list):
        """Fetch data for ODOO.BALANCE.TAG formulas.

        Compared to the core implementation, ``tax_tag_ids`` may be supplied
        without any account tag. Requests without tax tags are delegated to
        the core method, preserving its behaviour.
        """
        results = []
        for args in args_list:
            tax_tag_ids = [
                tag_id for tag_id in args.get("tax_tag_ids", []) if tag_id
            ]
            if not tax_tag_ids:
                results.extend(super().spreadsheet_fetch_balance_tag([args]))
                continue

            company_id = args["company_id"] or self.env.company.id
            domain = self._build_spreadsheet_formula_domain(args)
            MoveLines = self.env["account.move.line"].with_company(company_id)
            [(balance,)] = MoveLines._read_group(domain, aggregates=["balance:sum"])
            results.append({"balance": balance or 0.0})

        return results

    def _build_spreadsheet_formula_domain(self, formula_params, default_accounts=False):
        if "account_tag_ids" in formula_params or "tax_tag_ids" in formula_params:
            return self._build_balance_tag_formula_domain(formula_params)

        # ODOO.BALANCE and the other code-based formulas keep the core date
        # semantics; the optional domain is simply ANDed with them.
        domain = super()._build_spreadsheet_formula_domain(
            formula_params, default_accounts=default_accounts
        )
        extra_domain = self._validate_extra_domain(formula_params.get("domain"))
        if extra_domain:
            domain = Domain.AND([domain, extra_domain])
        return domain

    def _build_balance_tag_formula_domain(self, formula_params):
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
        tax_tag_ids = [
            int(tag_id)
            for tag_id in formula_params.get("tax_tag_ids", [])
            if tag_id
        ]

        if tag_ids:
            account_domain = Domain("account_id.tag_ids", "in", tag_ids)
        elif tax_tag_ids:
            # Tax tags can be used without filtering on account tags.
            account_domain = Domain.TRUE
        else:
            account_domain = Domain.FALSE

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

        if tax_tag_ids:
            domain &= Domain("tax_tag_ids", "in", tax_tag_ids)

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

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class SpreadsheetAccountBalanceDomainFunctionTest(AccountTestInvoicingCommon):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tag_1 = cls._create_account_tag("tag_1")
        cls.tag_2 = cls._create_account_tag("tag_2")
        cls.tag_3 = cls._create_account_tag("tag_3")
        cls.tax_tag = cls.env["account.account.tag"].create([{
            "name": "+TEST_BALANCE_DOMAIN",
            "applicability": "taxes",
        }])

        cls.company_data["default_account_receivable"].tag_ids |= cls.tag_1
        cls.company_data["default_account_revenue"].tag_ids |= cls.tag_1
        cls.company_data["default_account_expense"].tag_ids |= cls.tag_2

        cls.posted_move = cls.env["account.move"].create({
            "company_id": cls.company_data["company"].id,
            "move_type": "entry",
            "date": "2025-01-01",
            "line_ids": [
                Command.create({
                    "name": "posted line debit 1",
                    "account_id": cls.company_data["default_account_receivable"].id,
                    "debit": 100,
                    "company_id": cls.company_data["company"].id,
                }),
                Command.create({
                    "name": "posted line debit 2",
                    "account_id": cls.company_data["default_account_revenue"].id,
                    "debit": 50,
                    "company_id": cls.company_data["company"].id,
                }),
                Command.create({
                    "name": "posted line credit 1",
                    "account_id": cls.company_data["default_account_expense"].id,
                    "credit": 150,
                    "company_id": cls.company_data["company"].id,
                }),
            ],
        })
        cls.posted_move.action_post()

        cls.draft_move = cls.env["account.move"].create({
            "company_id": cls.company_data["company"].id,
            "move_type": "entry",
            "date": "2024-01-01",
            "line_ids": [
                Command.create({
                    "name": "draft line debit 1",
                    "account_id": cls.company_data["default_account_receivable"].id,
                    "debit": 100,
                    "company_id": cls.company_data["company"].id,
                }),
                Command.create({
                    "name": "draft line credit 1",
                    "account_id": cls.company_data["default_account_expense"].id,
                    "credit": 100,
                    "company_id": cls.company_data["company"].id,
                }),
            ],
        })

    @classmethod
    def _create_account_tag(cls, tag_name):
        return cls.env["account.account.tag"].create([{
            "name": tag_name,
            "applicability": "accounts",
        }])

    def _create_prior_year_move(self):
        """Posted 2024 move: tag_1 receivable debit / tag_2 expense credit."""
        move = self.env["account.move"].create({
            "company_id": self.company_data["company"].id,
            "move_type": "entry",
            "date": "2024-06-01",
            "line_ids": [
                Command.create({
                    "name": "prior year debit",
                    "account_id": self.company_data["default_account_receivable"].id,
                    "debit": 200,
                    "company_id": self.company_data["company"].id,
                }),
                Command.create({
                    "name": "prior year credit",
                    "account_id": self.company_data["default_account_expense"].id,
                    "credit": 200,
                    "company_id": self.company_data["company"].id,
                }),
            ],
        })
        move.action_post()
        return move

    def _create_extra_receivable_line(self):
        """Posted 2025 receivable debit of 25, named 'extra line'."""
        move = self.env["account.move"].create({
            "company_id": self.company_data["company"].id,
            "move_type": "entry",
            "date": "2025-02-01",
            "line_ids": [
                Command.create({
                    "name": "extra line",
                    "account_id": self.company_data["default_account_receivable"].id,
                    "debit": 25,
                    "company_id": self.company_data["company"].id,
                }),
                Command.create({
                    "name": "extra line credit",
                    "account_id": self.company_data["default_account_expense"].id,
                    "credit": 25,
                    "company_id": self.company_data["company"].id,
                }),
            ],
        })
        move.action_post()
        return move

    def _create_tax_tagged_move(self):
        """Posted 2025 move with tax tags on the receivable and expense lines."""
        move = self.env["account.move"].create({
            "company_id": self.company_data["company"].id,
            "move_type": "entry",
            "date": "2025-03-01",
            "line_ids": [
                Command.create({
                    "name": "tax tagged debit",
                    "account_id": self.company_data["default_account_receivable"].id,
                    "debit": 80,
                    "tax_tag_ids": [Command.set(self.tax_tag.ids)],
                    "company_id": self.company_data["company"].id,
                }),
                Command.create({
                    "name": "tax tagged credit",
                    "account_id": self.company_data["default_account_expense"].id,
                    "credit": 30,
                    "tax_tag_ids": [Command.set(self.tax_tag.ids)],
                    "company_id": self.company_data["company"].id,
                }),
                Command.create({
                    "name": "untagged balancing credit",
                    "account_id": self.company_data["default_account_expense"].id,
                    "credit": 50,
                    "company_id": self.company_data["company"].id,
                }),
            ],
        })
        move.action_post()
        return move

    # ------------------------------------------------------------------
    # ODOO.BALANCE.TAG helpers
    # ------------------------------------------------------------------

    def _args(self, tag_ids=None, date_range=None, company_id=None,
              include_unposted=False, domain=None, tax_tag_ids=None):
        return {
            "date_range": date_range or {"range_type": "year", "year": 2025},
            "account_tag_ids": tag_ids or [],
            "company_id": company_id,
            "include_unposted": include_unposted,
            "domain": domain,
            "tax_tag_ids": tax_tag_ids or [],
        }

    def _call(self, *args_list):
        return self.env["account.account"].spreadsheet_fetch_balance_tag(list(args_list))

    # ------------------------------------------------------------------
    # ODOO.BALANCE helpers
    # ------------------------------------------------------------------

    def _debit_credit_args(self, codes, date_range=None, company_id=None,
                           include_unposted=False, domain=None):
        return {
            "date_range": date_range or {"range_type": "year", "year": 2025},
            "codes": codes,
            "company_id": company_id,
            "include_unposted": include_unposted,
            "domain": domain,
        }

    def _call_debit_credit(self, *args_list):
        return self.env["account.account"].spreadsheet_fetch_debit_credit(
            list(args_list)
        )

    # ------------------------------------------------------------------
    # ODOO.BALANCE.TAG: base behaviour
    # ------------------------------------------------------------------

    def test_empty_payload(self):
        self.assertEqual(self._call(), [])

    def test_single_tag_posted_only(self):
        result = self._call(self._args(tag_ids=self.tag_1.ids))
        self.assertEqual(result, [{"balance": 150.0}])

    def test_multiple_tags(self):
        """tag_1 OR tag_2 matches all three accounts; their balances net to 0."""
        result = self._call(
            self._args(tag_ids=(self.tag_1 + self.tag_2).ids)
        )
        self.assertEqual(result, [{"balance": 0.0}])

    def test_draft_excluded(self):
        result = self._call(
            self._args(
                tag_ids=self.tag_1.ids,
                date_range={"range_type": "year", "year": 2024},
                include_unposted=False,
            )
        )
        self.assertEqual(result, [{"balance": 0.0}])

    def test_draft_included(self):
        result = self._call(
            self._args(
                tag_ids=self.tag_1.ids,
                date_range={"range_type": "year", "year": 2024},
                include_unposted=True,
            )
        )
        self.assertEqual(result, [{"balance": 100.0}])

    def test_no_tags_returns_zero(self):
        result = self._call(self._args(tag_ids=[]))
        self.assertEqual(result, [{"balance": 0}])

    # ------------------------------------------------------------------
    # ODOO.BALANCE.TAG: date semantics
    # ------------------------------------------------------------------

    def test_period_excludes_prior_year_for_all_account_types(self):
        """Year/quarter/month ranges sum only movements within the period."""
        self._create_prior_year_move()

        year_result = self._call(
            self._args(
                tag_ids=self.tag_1.ids,
                date_range={"range_type": "year", "year": 2025},
            )
        )
        quarter_result = self._call(
            self._args(
                tag_ids=self.tag_1.ids,
                date_range={"range_type": "quarter", "year": 2025, "quarter": 1},
            )
        )
        month_result = self._call(
            self._args(
                tag_ids=self.tag_1.ids,
                date_range={"range_type": "month", "year": 2025, "month": 1},
            )
        )
        self.assertEqual(year_result, [{"balance": 150.0}])
        self.assertEqual(quarter_result, [{"balance": 150.0}])
        self.assertEqual(month_result, [{"balance": 150.0}])

    def test_day_range_is_as_of_for_all_account_types(self):
        """A day range is an end date: balance up to that date, all accounts."""
        self._create_prior_year_move()

        day_result = self._call(
            self._args(
                tag_ids=self.tag_1.ids,
                date_range={"range_type": "day", "year": 2025, "month": 12, "day": 31},
            )
        )
        # receivable (tag_1): 2024 posted 200 + 2025 posted 100
        # revenue (tag_1): 2025 posted 50
        self.assertEqual(day_result, [{"balance": 350.0}])

    # ------------------------------------------------------------------
    # ODOO.BALANCE.TAG: extra domain
    # ------------------------------------------------------------------

    def test_extra_domain_filter_by_name(self):
        result = self._call(
            self._args(
                tag_ids=self.tag_1.ids,
                domain=[("name", "ilike", "debit 1")],
            )
        )
        self.assertEqual(result, [{"balance": 100.0}])

    def test_extra_domain_filter_by_debit(self):
        result = self._call(
            self._args(
                tag_ids=self.tag_1.ids,
                domain=[("debit", ">", 60)],
            )
        )
        self.assertEqual(result, [{"balance": 100.0}])

    def test_extra_domain_empty(self):
        result_none = self._call(self._args(tag_ids=self.tag_1.ids, domain=None))
        result_empty = self._call(self._args(tag_ids=self.tag_1.ids, domain=[]))
        expected = [{"balance": 150.0}]
        self.assertEqual(result_none, expected)
        self.assertEqual(result_empty, expected)

    def test_extra_domain_no_match(self):
        result = self._call(
            self._args(
                tag_ids=self.tag_1.ids,
                domain=[("partner_id", "in", [999])],
            )
        )
        self.assertEqual(result, [{"balance": 0.0}])

    def test_extra_domain_json_string(self):
        result = self._call(
            self._args(
                tag_ids=self.tag_1.ids,
                domain='[["debit", ">", 60]]',
            )
        )
        self.assertEqual(result, [{"balance": 100.0}])

    def test_extra_domain_invalid_returns_error(self):
        """safe_batch isolates invalid domains as a per-request error."""
        result = self._call(
            self._args(
                tag_ids=self.tag_1.ids,
                domain='["not", "a", "valid", "domain"]',
            )
        )
        self.assertEqual(len(result), 1)
        self.assertIn("__error__", result[0])

    def test_validate_extra_domain_direct_raises(self):
        with self.assertRaises(UserError):
            self.env["account.account"]._validate_extra_domain("not json")

    def test_unknown_field_returns_error(self):
        result = self._call(
            self._args(
                tag_ids=self.tag_1.ids,
                domain=[("not_a_field", "=", 1)],
            )
        )
        self.assertIn("__error__", result[0])

    def test_multiple_args_with_extra_domain(self):
        result = self._call(
            self._args(tag_ids=self.tag_1.ids),
            self._args(
                tag_ids=self.tag_1.ids,
                domain=[("debit", ">", 60)],
            ),
        )
        self.assertEqual(result, [
            {"balance": 150.0},
            {"balance": 100.0},
        ])

    def test_batch_isolation(self):
        result = self._call(
            self._args(tag_ids=self.tag_1.ids, domain="not json"),
            self._args(
                tag_ids=self.tag_1.ids,
                domain=[("debit", ">", 60)],
            ),
        )
        self.assertIn("__error__", result[0])
        self.assertEqual(result[1], {"balance": 100.0})

    def test_domain_cannot_bypass_company(self):
        company = self.company_data["company"]
        result = self._call(
            self._args(
                tag_ids=self.tag_1.ids,
                company_id=company.id,
                domain=[("company_id", "!=", company.id)],
            )
        )
        self.assertEqual(result, [{"balance": 0.0}])

    def test_empty_tags_with_invalid_domain_returns_zero(self):
        result = self._call(self._args(tag_ids=[], domain="not json"))
        self.assertEqual(result, [{"balance": 0}])

    # ------------------------------------------------------------------
    # ODOO.BALANCE.TAG: tax tags
    # ------------------------------------------------------------------

    def test_tax_tag_only_filters_all_accounts(self):
        """Tax tags can be used without any account tag."""
        self._create_tax_tagged_move()
        result = self._call(
            self._args(tag_ids=[], tax_tag_ids=self.tax_tag.ids)
        )
        # receivable debit 80 + expense credit 30
        self.assertEqual(result, [{"balance": 50.0}])

    def test_tax_tag_combined_with_account_tag(self):
        """Account tags and tax tags are ANDed."""
        self._create_tax_tagged_move()
        result = self._call(
            self._args(
                tag_ids=self.tag_1.ids,
                tax_tag_ids=self.tax_tag.ids,
            )
        )
        # tag_1 matches the receivable line (80); the expense line (30) is tag_2
        self.assertEqual(result, [{"balance": 80.0}])

    def test_tax_tag_only_respects_period_semantics(self):
        self._create_tax_tagged_move()
        result = self._call(
            self._args(
                tag_ids=[],
                date_range={"range_type": "year", "year": 2024},
                tax_tag_ids=self.tax_tag.ids,
            )
        )
        self.assertEqual(result, [{"balance": 0.0}])

    def test_tax_tag_with_extra_domain(self):
        self._create_tax_tagged_move()
        result = self._call(
            self._args(
                tag_ids=[],
                tax_tag_ids=self.tax_tag.ids,
                domain=[("debit", ">", 50)],
            )
        )
        self.assertEqual(result, [{"balance": 80.0}])

    def test_tax_tag_unknown_returns_zero(self):
        self._create_tax_tagged_move()
        result = self._call(
            self._args(tag_ids=[], tax_tag_ids=[999999])
        )
        self.assertEqual(result, [{"balance": 0.0}])

    def test_tax_tag_empty_behaves_like_core(self):
        self._create_tax_tagged_move()
        result = self._call(self._args(tag_ids=[], tax_tag_ids=[]))
        self.assertEqual(result, [{"balance": 0}])

    def test_tax_tag_batch(self):
        self._create_tax_tagged_move()
        result = self._call(
            self._args(tag_ids=[], tax_tag_ids=self.tax_tag.ids),
            self._args(
                tag_ids=self.tag_1.ids,
                tax_tag_ids=self.tax_tag.ids,
            ),
        )
        self.assertEqual(result, [{"balance": 50.0}, {"balance": 80.0}])

    # ------------------------------------------------------------------
    # ODOO.BALANCE
    # ------------------------------------------------------------------

    def test_balance_without_domain_keeps_core_semantics(self):
        """Balance-sheet accounts include prior-year lines up to period end."""
        self._create_prior_year_move()
        result = self._call_debit_credit(
            self._debit_credit_args(
                codes=[self.company_data["default_account_receivable"].code]
            )
        )
        self.assertEqual(result, [{"debit": 300.0, "credit": 0.0}])

    def test_balance_domain_filters_lines(self):
        self._create_extra_receivable_line()
        code = self.company_data["default_account_receivable"].code

        without_domain = self._call_debit_credit(
            self._debit_credit_args(codes=[code])
        )
        by_name = self._call_debit_credit(
            self._debit_credit_args(
                codes=[code],
                domain=[("name", "ilike", "extra line")],
            )
        )
        by_amount = self._call_debit_credit(
            self._debit_credit_args(
                codes=[code],
                domain=[("debit", ">", 60)],
            )
        )

        self.assertEqual(without_domain, [{"debit": 125.0, "credit": 0.0}])
        self.assertEqual(by_name, [{"debit": 25.0, "credit": 0.0}])
        self.assertEqual(by_amount, [{"debit": 100.0, "credit": 0.0}])

    def test_balance_domain_json_string(self):
        self._create_extra_receivable_line()
        code = self.company_data["default_account_receivable"].code
        result = self._call_debit_credit(
            self._debit_credit_args(
                codes=[code],
                domain='[["debit", ">", 60]]',
            )
        )
        self.assertEqual(result, [{"debit": 100.0, "credit": 0.0}])

    def test_balance_domain_narrows_opening_balance(self):
        self._create_prior_year_move()
        code = self.company_data["default_account_receivable"].code
        result = self._call_debit_credit(
            self._debit_credit_args(
                codes=[code],
                domain=[("date", ">=", "2025-01-01")],
            )
        )
        self.assertEqual(result, [{"debit": 100.0, "credit": 0.0}])

    def test_balance_domain_cannot_bypass_company(self):
        company = self.company_data["company"]
        code = self.company_data["default_account_receivable"].code
        result = self._call_debit_credit(
            self._debit_credit_args(
                codes=[code],
                company_id=company.id,
                domain=[("company_id", "!=", company.id)],
            )
        )
        self.assertEqual(result, [{"debit": 0, "credit": 0}])

    def test_balance_invalid_domain_returns_error(self):
        code = self.company_data["default_account_receivable"].code
        result = self._call_debit_credit(
            self._debit_credit_args(codes=[code], domain="not json")
        )
        self.assertIn("__error__", result[0])

    def test_balance_batch_isolation(self):
        code = self.company_data["default_account_receivable"].code
        result = self._call_debit_credit(
            self._debit_credit_args(codes=[code], domain="not json"),
            self._debit_credit_args(
                codes=[code],
                domain=[("debit", ">", 60)],
            ),
        )
        self.assertIn("__error__", result[0])
        self.assertEqual(result[1], {"debit": 100.0, "credit": 0.0})

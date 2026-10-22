import { EvaluationError, helpers, registries } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { parseAccountingDate } from "@spreadsheet_account/accounting_functions";
import { BalanceDomainAccountingPlugin } from "./plugins/accounting_plugin";

const { evaluationPluginRegistry, functionRegistry } = registries;
const { arg, toBoolean, toNumber, toString } = helpers;

const FUNCTION_NAME = "ODOO.BALANCE.TAG";

evaluationPluginRegistry.replace("odooAccountingAggregates", BalanceDomainAccountingPlugin);

const coreFormula = functionRegistry.get(FUNCTION_NAME);
const coreCompute = coreFormula.compute;

const DOMAIN_ARG = arg(
    "domain (string, optional)",
    _t(
        "Extra Odoo domain over account.move.line, as a JSON-encoded list of "
        + '[field, operator, value] conditions. Example: \'[["debit", ">", 50]]\'.'
    )
);

function computeBalanceTagWithDomain(
    accountTagIds,
    dateRange,
    offset = { value: 0 },
    companyId = { value: null },
    includeUnposted = { value: false },
    domain = { value: null }
) {
    const domainString = toString(domain).trim();
    if (!domainString) {
        return coreCompute.apply(this, arguments);
    }

    const _accountTagIds = toString(accountTagIds)
        .split(",")
        .map((tagId) => toNumber(tagId, this.locale))
        .sort();
    const _offset = toNumber(offset, this.locale);

    if (!dateRange?.value) {
        dateRange = { value: new Date().getFullYear() };
    }
    const _dateRange = parseAccountingDate(dateRange, this.locale);
    if (_dateRange.year + _offset < 1900) {
        throw new EvaluationError(
            _t("%s is not a valid year.", _dateRange.year + _offset)
        );
    }

    const _companyId = toNumber(companyId, this.locale);
    const _includeUnposted = toBoolean(includeUnposted);
    const _accountTagData = this.getters.getAccountTagData(
        _accountTagIds,
        _dateRange,
        _offset,
        _companyId,
        _includeUnposted,
        domainString
    );
    if (_accountTagData === false) {
        return new EvaluationError(
            _t("The balance for given account tag could not be computed.")
        );
    }

    const currency = this.getters.getCompanyCurrency(_companyId);
    if (currency === false) {
        throw new EvaluationError(_t("Currency not available for this company."));
    }
    return {
        value: _accountTagData.balance,
        format: this.getters.getCompanyCurrencyFormat(_companyId) || "#,##0.00",
    };
}

if (coreFormula.args.length === 5) {
    functionRegistry.replace(FUNCTION_NAME, {
        ...coreFormula,
        args: [...coreFormula.args, DOMAIN_ARG],
        compute: computeBalanceTagWithDomain,
    });
} else {
    console.error(
        `spreadsheet_account_balance_domain: unexpected ${FUNCTION_NAME} signature; ` +
        "the optional domain argument was not installed."
    );
}

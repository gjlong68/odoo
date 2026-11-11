import { EvaluationError, helpers, registries } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { parseAccountingDate } from "@spreadsheet_account/accounting_functions";
import { BalanceDomainAccountingPlugin } from "./plugins/accounting_plugin";

const { evaluationPluginRegistry, functionRegistry } = registries;
const { arg, toBoolean, toNumber, toString } = helpers;

evaluationPluginRegistry.replace("odooAccountingAggregates", BalanceDomainAccountingPlugin);

function makeDomainArg() {
    return arg(
        "domain (string, optional)",
        _t(
            "Extra Odoo domain over account.move.line, as a JSON-encoded list of "
            + '[field, operator, value] conditions. Example: \'[["debit", ">", 50]]\'.'
        )
    );
}

function makeTaxTagArg() {
    return arg(
        "tax_tag_ids (string, optional)",
        _t(
            "Tax tag ids (separated by a comma) used to filter account.move.line "
            + "tax tags. Can be used without account tags."
        )
    );
}

function getCurrencyFormatOrThrow(getters, companyId) {
    const currency = getters.getCompanyCurrency(companyId);
    if (currency === false) {
        throw new EvaluationError(_t("Currency not available for this company."));
    }
    return getters.getCompanyCurrencyFormat(companyId) || "#,##0.00";
}

function replaceWithOptionalArgs(functionName, extraArgs, compute) {
    const coreFormula = functionRegistry.get(functionName);
    if (coreFormula.args.length === 5) {
        functionRegistry.replace(functionName, {
            ...coreFormula,
            args: [...coreFormula.args, ...extraArgs],
            compute,
        });
    } else {
        console.error(
            `spreadsheet_account_balance_domain: unexpected ${functionName} signature; ` +
            "the optional arguments were not installed."
        );
    }
}

// ---------------------------------------------------------------------------
// ODOO.BALANCE.TAG
// ---------------------------------------------------------------------------

const coreBalanceTagCompute = functionRegistry.get("ODOO.BALANCE.TAG").compute;

function computeBalanceTagWithDomain(
    accountTagIds,
    dateRange,
    offset = { value: 0 },
    companyId = { value: null },
    includeUnposted = { value: false },
    domain = { value: null },
    taxTagIds = { value: null }
) {
    const domainString = toString(domain).trim();
    const _taxTagIds = toString(taxTagIds)
        .split(",")
        .map((tagId) => toNumber(tagId, this.locale))
        .filter((tagId) => tagId)
        .sort();

    if (!domainString && !_taxTagIds.length) {
        return coreBalanceTagCompute.apply(this, arguments);
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
        domainString || null,
        _taxTagIds
    );
    if (_accountTagData === false) {
        return new EvaluationError(
            _t("The balance for given account tag could not be computed.")
        );
    }

    return {
        value: _accountTagData.balance,
        format: getCurrencyFormatOrThrow(this.getters, _companyId),
    };
}

replaceWithOptionalArgs(
    "ODOO.BALANCE.TAG",
    [makeDomainArg(), makeTaxTagArg()],
    computeBalanceTagWithDomain
);

// ---------------------------------------------------------------------------
// ODOO.BALANCE
// ---------------------------------------------------------------------------

const coreBalanceCompute = functionRegistry.get("ODOO.BALANCE").compute;

function computeBalanceWithDomain(
    accountCodes,
    dateRange,
    offset = { value: 0 },
    companyId = { value: null },
    includeUnposted = { value: false },
    domain = { value: null }
) {
    const domainString = toString(domain).trim();
    if (!domainString) {
        return coreBalanceCompute.apply(this, arguments);
    }

    const _accountCodes = toString(accountCodes)
        .split(",")
        .map((code) => code.trim())
        .sort();
    const _offset = toNumber(offset, this.locale);
    const _dateRange = parseAccountingDate(dateRange, this.locale);
    if (_dateRange.year + _offset < 1900) {
        throw new EvaluationError(
            _t("%s is not a valid year.", _dateRange.year + _offset)
        );
    }
    const _companyId = companyId.value === null ? null : toNumber(companyId.value, this.locale);
    const _includeUnposted = toBoolean(includeUnposted);
    const value =
        this.getters.getAccountPrefixDebit(
            _accountCodes,
            _dateRange,
            _offset,
            _companyId,
            _includeUnposted,
            domainString
        ) -
        this.getters.getAccountPrefixCredit(
            _accountCodes,
            _dateRange,
            _offset,
            _companyId,
            _includeUnposted,
            domainString
        );

    return { value, format: getCurrencyFormatOrThrow(this.getters, _companyId) };
}

replaceWithOptionalArgs("ODOO.BALANCE", [makeDomainArg()], computeBalanceWithDomain);

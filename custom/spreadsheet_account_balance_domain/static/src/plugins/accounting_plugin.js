// @ts-check
import { AccountingPlugin } from "@spreadsheet_account/plugins/accounting_plugin";
import { camelToSnakeObject } from "@spreadsheet/helpers/helpers";
import { deepCopy } from "@web/core/utils/objects";

/**
 * Extends the core accounting plugin so that ODOO.BALANCE.TAG and
 * ODOO.BALANCE can forward an optional extra domain to the server, and
 * ODOO.BALANCE.TAG can filter on tax tags.
 */
export class BalanceDomainAccountingPlugin extends AccountingPlugin {
    /**
     * @param {number[]} accountTagIds
     * @param {object} dateRange
     * @param {number} offset
     * @param {number | null} companyId
     * @param {boolean} includeUnposted
     * @param {string | null} [domain] JSON-encoded extra Odoo domain
     * @param {number[]} [taxTagIds] tax tag ids
     */
    getAccountTagData(
        accountTagIds,
        dateRange,
        offset,
        companyId,
        includeUnposted,
        domain,
        taxTagIds
    ) {
        const hasTaxTags = Array.isArray(taxTagIds) && taxTagIds.length > 0;
        if (!domain && !hasTaxTags) {
            return super.getAccountTagData(
                accountTagIds,
                dateRange,
                offset,
                companyId,
                includeUnposted
            );
        }
        dateRange = deepCopy(dateRange);
        dateRange.year += offset;
        const params = {
            accountTagIds,
            dateRange,
            companyId,
            includeUnposted,
            taxTagIds: taxTagIds || [],
        };
        if (domain) {
            params.domain = domain;
        }
        return this.serverData.batch.get(
            "account.account",
            "spreadsheet_fetch_balance_tag",
            camelToSnakeObject(params)
        );
    }

    /**
     * @param {string[]} codes
     * @param {object} dateRange
     * @param {number} offset
     * @param {number | null} companyId
     * @param {boolean} includeUnposted
     * @param {string | null} [domain] JSON-encoded extra Odoo domain
     * @returns {{ debit: number, credit: number }}
     */
    _fetchAccountData(codes, dateRange, offset, companyId, includeUnposted, domain) {
        if (!domain) {
            return super._fetchAccountData(
                codes,
                dateRange,
                offset,
                companyId,
                includeUnposted
            );
        }
        dateRange = deepCopy(dateRange);
        dateRange.year += offset;
        return this.serverData.batch.get(
            "account.account",
            "spreadsheet_fetch_debit_credit",
            camelToSnakeObject({ dateRange, codes, companyId, includeUnposted, domain })
        );
    }

    getAccountPrefixCredit(codes, dateRange, offset, companyId, includeUnposted, domain) {
        return this._fetchAccountData(
            codes,
            dateRange,
            offset,
            companyId,
            includeUnposted,
            domain
        ).credit;
    }

    getAccountPrefixDebit(codes, dateRange, offset, companyId, includeUnposted, domain) {
        return this._fetchAccountData(
            codes,
            dateRange,
            offset,
            companyId,
            includeUnposted,
            domain
        ).debit;
    }
}

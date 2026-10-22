// @ts-check
import { AccountingPlugin } from "@spreadsheet_account/plugins/accounting_plugin";
import { camelToSnakeObject } from "@spreadsheet/helpers/helpers";
import { deepCopy } from "@web/core/utils/objects";

/**
 * Extends the core accounting plugin so that ODOO.BALANCE.TAG can forward an
 * optional extra domain to spreadsheet_fetch_balance_tag.
 */
export class BalanceDomainAccountingPlugin extends AccountingPlugin {
    /**
     * @param {number[]} accountTagIds
     * @param {object} dateRange
     * @param {number} offset
     * @param {number | null} companyId
     * @param {boolean} includeUnposted
     * @param {string | null} [domain] JSON-encoded extra Odoo domain
     */
    getAccountTagData(accountTagIds, dateRange, offset, companyId, includeUnposted, domain) {
        if (!domain) {
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
        return this.serverData.batch.get(
            "account.account",
            "spreadsheet_fetch_balance_tag",
            camelToSnakeObject({ accountTagIds, dateRange, companyId, includeUnposted, domain })
        );
    }
}

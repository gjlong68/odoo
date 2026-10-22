import { proxy, useEffect } from "@odoo/owl";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";
import { StockReportSearchModel } from "@stock/views/search/stock_report_search_model";
import { StockReportSearchPanel } from "@stock/views/search/stock_report_search_panel";

// `luxon` is a global library in Odoo 20 (not an AMD module), same as in
// web/static/src/core/l10n/dates.js.
const { DateTime } = globalThis.luxon;

// Bridge the report context (`to_date`) to the panel's local date state. The
// state must survive a reuse/reload of the Stock report view: in that case
// the panel is not re-created and its setup() is not called again.
const inventoryDateState = proxy({ toDate: false });

// Temporary diagnostic: inspect in the browser console with
// window.__zdInventoryAtDate?.toDate
window.__zdInventoryAtDate = inventoryDateState;

function parseInventoryDate(toDate) {
    if (typeof toDate !== "string" || !toDate) {
        return false;
    }
    // Date-only strings mean end-of-day in the core quantity computation.
    return toDate.length === 10
        ? DateTime.fromISO(toDate).endOf("day")
        : deserializeDateTime(toDate);
}

patch(StockReportSearchModel.prototype, {
    async load(...args) {
        const result = await super.load(...args);
        inventoryDateState.toDate = this.globalContext?.to_date || false;
        return result;
    },
    async reload(...args) {
        const result = await super.reload(...args);
        inventoryDateState.toDate = this.globalContext?.to_date || false;
        return result;
    },
    applyDateContext(date) {
        inventoryDateState.toDate = date || false;
        return super.applyDateContext(date);
    },
});

patch(StockReportSearchPanel.prototype, {
    setup() {
        super.setup(...arguments);
        useEffect(() => {
            const toDate = inventoryDateState.toDate;
            const current = this.dateState.inventoryDate;
            if (!toDate) {
                if (current) {
                    this.dateState.inventoryDate = false;
                }
                return;
            }
            const parsed = parseInventoryDate(toDate);
            if (!current || !current.equals(parsed)) {
                this.dateState.inventoryDate = parsed;
            }
        });
    },
});

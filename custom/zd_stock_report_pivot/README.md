# Stock Report Pivot

Extends Inventory → Reporting with:

- a **Pivot** view on `product.product` (variant level, On Hand, Amount, Free to Use, Incoming,
  Outgoing, Forecasted);
- an **Inventory at Date** menu: choose a date and open the Stock report with quantities computed
  at the end of that date;
- a **Stock by Company** pivot/list report grouping stock by **inventory company**
  (the company of the stock location/warehouse) and product category.

The Stock report is based on `product.product`, whose quantity fields are non-stored computed
fields. The module implements the core `id:recordset` read-group pattern so these fields can be
used as pivot measures, and it forwards the selected date through the standard `to_date` context
used by `product.product._compute_quantities_dict()`.

## Stock by Company

`Stock by Company` is based on `zd_stock_report_pivot.stock_company_report`, a read-only SQL-view
model with one row per (product, company) pair. The company is the company of the stock location,
falling back to the company of its warehouse. The quantity fields are computed with the core
`product.product` logic restricted to that company (`allowed_company_ids`), so On Hand, Free to
Use, Incoming, Outgoing and Forecasted match the standard Stock report for the same company.
The **Amount** measure is the on-hand quantity multiplied by the product cost (`standard_price`)
of the row company; at a historical date the quantity of that date is used with the current cost.

Default pivot rows are **Company → Product Category → Product Variant**. Product rows use the
variant (`product_id`, e.g. `C12P (Cream)` / `C12P (Hazelnut)`), not the product template, so
variants of the same product are reported separately. A **Product Template** group-by is also
available when template-level aggregation is needed.

Rows only exist for pairs with current stock, pending moves or historical done moves; the last
one keeps the report usable for any inventory date (a `to_date` context is forwarded to the core
computation).

To query a historical date, open **Inventory → Reporting → Inventory at Date**, pick a date and
click **Open Stock by Company**.

## Dependencies

`stock`

## Install

```bash
make install MODULE=zd_stock_report_pivot
```

## Test

```bash
make test MODULE=zd_stock_report_pivot
```

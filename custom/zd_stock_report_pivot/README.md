# Stock Report Pivot

Extends Inventory → Reporting → Stock with:

- a **Pivot** view on `product.product` (On Hand, Free to Use, Incoming, Outgoing, Forecasted);
- an **Inventory at Date** menu: choose a date and open the Stock report with quantities computed
  at the end of that date.

The Stock report is based on `product.product`, whose quantity fields are non-stored computed
fields. The module implements the core `id:recordset` read-group pattern so these fields can be
used as pivot measures, and it forwards the selected date through the standard `to_date` context
used by `product.product._compute_quantities_dict()`.

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

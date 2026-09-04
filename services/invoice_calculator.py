"""Single source of truth for the customer-payable invoice total (F1.5).

The authoritative Customer Payable formula is::

    prediscount    = parts_cost + labor_cost + additional_charges
    after_discount = max(0, prediscount - discount)
    tax_amount     = int(after_discount * tax_rate / 100)
    total (payable) = after_discount + tax_amount

Semantics are pinned from the InvoiceWidget behaviour (the amount the
shop actually quotes on the Financial tab), per the F1 data-domain audit
("Independent Senior Accounting Architecture Review", §7 and §12):

  * additional charges ARE part of the customer payable
  * discount (a flat amount) is applied BEFORE tax
  * the tax rate is a percentage; ``tax_amount`` truncates to ``int``
  * a discount larger than the prediscount base clamps the base to 0
    (a negative payable is never produced)

All monetary amounts are integer currency units; only the tax rate is a
float percentage. Malformed/missing inputs degrade safely to 0.

Conceptual invariants (FINANCIAL_ROADMAP.md §5, audit §19):

  * ``parts_cost``/``labor_cost``/``additional_charges`` here are
    CUSTOMER SALE amounts (snapshots). Shop purchase cost is a different
    concept owned by ``ProfitService`` (``purchase_price_snapshot``) and
    must never be substituted here.
  * This function is the single owner of the payable formula. UI code
    (InvoiceWidget, table_service, invoice_generator) must call it —
    never re-implement it.
"""
from typing import Any, Dict, List


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _additional_charges_total(charges: Any) -> int:
    """Sum additional-charge line totals.

    Mirrors ProfitService.additional_charge_revenue: uses
    ``total_price`` and falls back to ``amount`` for legacy charge
    lines that only carry an amount.
    """
    total = 0
    if not isinstance(charges, (list, tuple)):
        return 0
    for charge in charges:
        if not isinstance(charge, dict):
            continue
        line_total = _to_int(charge.get('total_price', 0))
        if line_total == 0:
            line_total = _to_int(charge.get('amount', 0))
        total += line_total
    return total


def calculate_invoice_totals(repair_data: Dict[str, Any]) -> Dict[str, Any]:
    """Return the authoritative customer-payable breakdown.

    Required keys of the result (superset of the historical contract so
    invoice_generator/table_service keep working):

      parts_cost          sale sum of part lines
      labor_cost          sum of service lines
      additional_charges  sum of additional-charge lines
      subtotal            prediscount base (parts + labor + charges)
      tax_rate            percentage (float)
      tax_amount          int(after_discount * tax_rate / 100)
      discount            flat discount amount
      after_discount      max(0, subtotal - discount)
      total               customer payable = after_discount + tax_amount
    """
    repair_data = repair_data or {}

    parts_cost = _to_int(repair_data.get('parts_cost', 0))
    labor_cost = _to_int(repair_data.get('labor_cost', 0))
    additional_charges = _additional_charges_total(
        repair_data.get('additional_charges')
    )

    try:
        tax_rate = float(repair_data.get('tax', 0) or 0)
    except (TypeError, ValueError):
        tax_rate = 0.0

    discount = _to_int(repair_data.get('discount', 0))

    subtotal = parts_cost + labor_cost + additional_charges
    after_discount = max(0, subtotal - discount)
    tax_amount = int(after_discount * tax_rate / 100)
    total = after_discount + tax_amount

    return {
        'parts_cost': parts_cost,
        'labor_cost': labor_cost,
        'additional_charges': additional_charges,
        'subtotal': subtotal,
        'tax_rate': tax_rate,
        'tax_amount': tax_amount,
        'discount': discount,
        'after_discount': after_discount,
        'total': total,
    }


def payable_total(repair_data: Dict[str, Any]) -> int:
    """Convenience accessor: the authoritative customer payable amount."""
    return calculate_invoice_totals(repair_data)['total']

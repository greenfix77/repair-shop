"""Compatibility shim for the invoice total (F1.5).

The duplicate formula that used to live here was removed: the single
source of truth for the customer payable is
``services.invoice_calculator.calculate_invoice_totals``. This module
keeps the historical ``calculate_invoice`` signature so existing callers
(table_service) keep working while delegating all math to the SSOT.
"""
from typing import Any, List, Optional, Tuple

from services.invoice_calculator import calculate_invoice_totals


def calculate_invoice(
    parts_cost: float,
    labor_cost: float,
    tax_rate: float,
    discount: float,
    additional_charges: Optional[List[Any]] = None,
) -> Tuple[float, float, float]:
    """Return ``(subtotal, tax_amount, total)`` via the single source of truth.

    ``subtotal`` is the prediscount base (parts + labor + additional
    charges) and ``total`` is the authoritative customer payable.
    """
    repair_data = {
        'parts_cost': parts_cost,
        'labor_cost': labor_cost,
        'tax': tax_rate,
        'discount': discount,
    }
    if additional_charges is not None:
        repair_data['additional_charges'] = additional_charges

    fin = calculate_invoice_totals(repair_data)
    return fin['subtotal'], fin['tax_amount'], fin['total']

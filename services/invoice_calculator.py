from typing import Dict, Any


def calculate_invoice_totals(repair_data: Dict[str, Any]) -> Dict[str, Any]:
    parts_cost = repair_data.get('parts_cost', 0)
    labor_cost = repair_data.get('labor_cost', 0)
    tax_rate = repair_data.get('tax', 0)
    discount = repair_data.get('discount', 0)

    subtotal = parts_cost + labor_cost
    tax_amount = subtotal * (tax_rate / 100)
    total = subtotal + tax_amount - discount

    return {
        'parts_cost': parts_cost,
        'labor_cost': labor_cost,
        'subtotal': subtotal,
        'tax_rate': tax_rate,
        'tax_amount': tax_amount,
        'discount': discount,
        'total': total,
    }

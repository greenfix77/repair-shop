from typing import Tuple


def calculate_invoice(
    parts_cost: float,
    labor_cost: float,
    tax_rate: float,
    discount: float
) -> Tuple[float, float, float]:
    subtotal = parts_cost + labor_cost
    tax_amount = subtotal * (tax_rate / 100)
    total = subtotal + tax_amount - discount
    return subtotal, tax_amount, total

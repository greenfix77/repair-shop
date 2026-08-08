"""Pure profit calculation service for repairs.

Phase 5F-1 introduces :class:`ProfitService`, the single owner of
repair profitability math. The service is intentionally pure:

  * no UI
  * no database access
  * no repositories
  * no persistence

It accepts a plain ``repair_dict`` and returns a structured profit
breakdown. Consumers (Dashboard, Reports, future analytics) can call
``calculate_profit`` without duplicating the formulas.

All inputs are coerced safely to numeric values so legacy or
partially-populated repair dicts never raise.
"""
from typing import Any, Dict, List, Optional


class ProfitService:
    """Compute repair profitability from a repair dict."""

    @staticmethod
    def _to_int(value: Any, default: int = 0) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _part_lines(cls, repair: Optional[Dict]) -> List[Dict]:
        if not isinstance(repair, dict):
            return []
        lines = repair.get('part_lines', []) or []
        return [l for l in lines if isinstance(l, dict)]

    @classmethod
    def _service_lines(cls, repair: Optional[Dict]) -> List[Dict]:
        if not isinstance(repair, dict):
            return []
        lines = repair.get('service_lines', []) or []
        return [l for l in lines if isinstance(l, dict)]

    @classmethod
    def _additional_charges(cls, repair: Optional[Dict]) -> List[Dict]:
        if not isinstance(repair, dict):
            return []
        charges = repair.get('additional_charges', []) or []
        return [c for c in charges if isinstance(c, dict)]

    @classmethod
    def parts_cost(cls, repair: Optional[Dict]) -> int:
        """``SUM(quantity * purchase_price_snapshot)`` across part lines."""
        total = 0
        for line in cls._part_lines(repair):
            qty = cls._to_int(line.get('quantity', 0))
            purchase = cls._to_int(line.get('purchase_price_snapshot', 0))
            total += qty * purchase
        return total

    @classmethod
    def parts_revenue(cls, repair: Optional[Dict]) -> int:
        """``SUM(quantity * unit_price)`` across part lines."""
        total = 0
        for line in cls._part_lines(repair):
            qty = cls._to_int(line.get('quantity', 0))
            unit_price = cls._to_int(line.get('unit_price', 0))
            total += qty * unit_price
        return total

    @classmethod
    def services_revenue(cls, repair: Optional[Dict]) -> int:
        """Existing labor/service subtotal."""
        total = 0
        for line in cls._service_lines(repair):
            total += cls._to_int(line.get('total_price', 0))
        return total

    @classmethod
    def additional_charge_revenue(cls, repair: Optional[Dict]) -> int:
        """Sum of additional charges."""
        total = 0
        for charge in cls._additional_charges(repair):
            total += cls._to_int(charge.get('total_price', 0))
            if total == 0:
                total += cls._to_int(charge.get('amount', 0))
        return total

    @classmethod
    def calculate_profit(cls, repair: Optional[Dict]) -> Dict[str, Any]:
        """Return a structured profit breakdown for ``repair``.

        Keys:
          - parts_cost:                ``SUM(qty * purchase_price_snapshot)``
          - parts_revenue:             ``SUM(qty * unit_price)``
          - services_revenue:          existing labor/service subtotal
          - additional_charge_revenue: sum of additional charges
          - gross_revenue:             parts + services + charges
          - gross_cost:                parts_cost
          - gross_profit:              gross_revenue - gross_cost
          - profit_margin:             gross_profit / gross_revenue,
                                       or 0 when revenue is 0
        """
        parts_cost = cls.parts_cost(repair)
        parts_revenue = cls.parts_revenue(repair)
        services_revenue = cls.services_revenue(repair)
        additional_charge_revenue = cls.additional_charge_revenue(repair)

        gross_revenue = (
            parts_revenue + services_revenue + additional_charge_revenue
        )
        gross_cost = parts_cost
        gross_profit = gross_revenue - gross_cost

        if gross_revenue > 0:
            profit_margin = gross_profit / gross_revenue
        else:
            profit_margin = 0.0

        return {
            'parts_cost': parts_cost,
            'parts_revenue': parts_revenue,
            'services_revenue': services_revenue,
            'additional_charge_revenue': additional_charge_revenue,
            'gross_revenue': gross_revenue,
            'gross_cost': gross_cost,
            'gross_profit': gross_profit,
            'profit_margin': profit_margin,
        }

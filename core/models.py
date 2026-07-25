from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class Repair:
    id: int = 0
    customer_name: str = ''
    phone: str = ''
    brand: str = ''
    model: str = ''
    issue: str = ''
    status: str = ''
    receive_date: str = ''
    delivery_date: str = ''
    parts_cost: int = 0
    labor_cost: int = 0
    tax: float = 0.0
    discount: int = 0
    notes: str = ''
    warranty: str = ''
    paid_amount: int = 0
    payment_status: str = 'پرداخت نشده'
    payment_method: str = 'نقدی'
    payment_date: str = ''
    financial_notes: str = ''
    service_lines: List[Dict] = field(default_factory=list)
    part_lines: List[Dict] = field(default_factory=list)
    additional_charges: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'phone': self.phone,
            'brand': self.brand,
            'model': self.model,
            'issue': self.issue,
            'status': self.status,
            'receive_date': self.receive_date,
            'delivery_date': self.delivery_date,
            'parts_cost': self.parts_cost,
            'labor_cost': self.labor_cost,
            'tax': self.tax,
            'discount': self.discount,
            'notes': self.notes,
            'warranty': self.warranty,
            'paid_amount': self.paid_amount,
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'payment_date': self.payment_date,
            'financial_notes': self.financial_notes,
            'service_lines': self.service_lines,
            'part_lines': self.part_lines,
            'additional_charges': self.additional_charges,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Repair':
        return cls(
            id=data.get('id', 0),
            customer_name=data.get('customer_name', ''),
            phone=data.get('phone', ''),
            brand=data.get('brand', ''),
            model=data.get('model', ''),
            issue=data.get('issue', ''),
            status=data.get('status', ''),
            receive_date=data.get('receive_date', ''),
            delivery_date=data.get('delivery_date', ''),
            parts_cost=data.get('parts_cost', 0),
            labor_cost=data.get('labor_cost', 0),
            tax=float(data.get('tax', 0)),
            discount=data.get('discount', 0),
            notes=data.get('notes', ''),
            warranty=data.get('warranty', ''),
            paid_amount=data.get('paid_amount', 0),
            payment_status=data.get('payment_status', 'پرداخت نشده'),
            payment_method=data.get('payment_method', 'نقدی'),
            payment_date=data.get('payment_date', ''),
            financial_notes=data.get('financial_notes', ''),
            service_lines=data.get('service_lines', []),
            part_lines=data.get('part_lines', []),
            additional_charges=data.get('additional_charges', []),
        )

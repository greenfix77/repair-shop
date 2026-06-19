from dataclasses import dataclass, field
from typing import Dict, Any


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
        )

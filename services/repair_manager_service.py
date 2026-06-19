from typing import List, Dict, Optional

from core.models import Repair


def add_repair(repairs: List[Dict], new_repair: Dict) -> List[Dict]:
    """
    Add a new repair to the repairs list.
    Assigns a unique ID to the new repair.
    """
    repair = Repair.from_dict(new_repair)

    existing_ids = [r['id'] for r in repairs if 'id' in r]
    repair.id = max(existing_ids) + 1 if existing_ids else 1

    updated_repairs = repairs.copy()
    updated_repairs.append(repair.to_dict())
    return updated_repairs


def delete_repair(repairs: List[Dict], repair_id: int) -> List[Dict]:
    """
    Delete a repair by ID from the repairs list.
    """
    return [r for r in repairs if r['id'] != repair_id]


def get_repair_by_id(repairs: List[Dict], repair_id: int) -> Optional[Dict]:
    """
    Find and return a repair by its ID.
    """
    for repair in repairs:
        if repair['id'] == repair_id:
            return repair
    return None


def update_repair(repairs: List[Dict], repair_id: int, updated_data: Dict) -> List[Dict]:
    """
    Update a repair by ID with new data.
    """
    repair = Repair.from_dict(updated_data)
    repair.id = repair_id

    updated_repairs = []
    for r in repairs:
        if r['id'] == repair_id:
            merged = {**r, **repair.to_dict()}
            merged['id'] = repair_id
            updated_repairs.append(merged)
        else:
            updated_repairs.append(r)
    return updated_repairs

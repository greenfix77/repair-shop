from typing import List, Dict, Optional


def add_repair(repairs: List[Dict], new_repair: Dict) -> List[Dict]:
    """
    Add a new repair to the repairs list.
    Assigns a unique ID to the new repair.
    """
    existing_ids = [r['id'] for r in repairs if 'id' in r]
    new_repair['id'] = max(existing_ids) + 1 if existing_ids else 1
    
    updated_repairs = repairs.copy()
    updated_repairs.append(new_repair)
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
    updated_repairs = []
    for repair in repairs:
        if repair['id'] == repair_id:
            # Merge the existing repair data with updated data
            updated_repair = {**repair, **updated_data}
            updated_repair['id'] = repair_id  # Ensure ID doesn't change
            updated_repairs.append(updated_repair)
        else:
            updated_repairs.append(repair)
    return updated_repairs
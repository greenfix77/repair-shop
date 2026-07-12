from typing import List, Dict, Tuple

from core.status import STATUS_DELIVERED, STATUS_COMPLETED


def _match_key(phone: str, name: str) -> Tuple[str, str]:
    """Build normalized lookup keys for a repair/customer link.

    Repairs are linked to customers by phone (preferred) or full name,
    mirroring the existing ``_has_related_repairs`` logic in app.py.
    """
    p = (phone or '').strip()
    n = (name or '').strip()
    return p, n


def compute_customer_repair_stats(
    repairs: List[Dict], customers: List[Dict]
) -> Dict[int, Dict[str, int]]:
    """Compute per-customer repair statistics in a single pass.

    Returns a dict keyed by customer ``id`` with values::

        {'total': int, 'delivered': int, 'in_progress': int}

    Repairs are matched to a customer when the repair's phone equals the
    customer's phone, or (when phone is absent) the repair's customer_name
    equals the customer's full_name. This matches the linkage already used
    by ``LaptopRepairManager._has_related_repairs``.

    Definitions (using project status values):
      - total        = all repairs linked to the customer
      - delivered    = repairs with status STATUS_DELIVERED or STATUS_COMPLETED
      - in_progress  = repairs not delivered/completed and not cancelled
                       (there is no cancelled status in core.status, so this
                       is every remaining repair)
    """
    by_phone = {}
    by_name = {}
    for c in customers:
        cid = c.get('id')
        if cid is None:
            continue
        phone, name = _match_key(c.get('phone', ''), c.get('full_name', ''))
        if phone:
            by_phone.setdefault(phone, []).append(cid)
        if name:
            by_name.setdefault(name, []).append(cid)

    stats: Dict[int, Dict[str, int]] = {}
    for c in customers:
        cid = c.get('id')
        if cid is None:
            continue
        stats[cid] = {'total': 0, 'delivered': 0, 'in_progress': 0}

    delivered_statuses = (STATUS_DELIVERED, STATUS_COMPLETED)

    for r in repairs:
        r_phone, r_name = _match_key(
            r.get('phone', ''), r.get('customer_name', '')
        )
        matched_ids = []
        if r_phone and r_phone in by_phone:
            matched_ids = by_phone[r_phone]
        elif r_name and r_name in by_name:
            matched_ids = by_name[r_name]

        if not matched_ids:
            continue

        status = r.get('status', '')
        is_delivered = status in delivered_statuses

        for cid in matched_ids:
            entry = stats.get(cid)
            if entry is None:
                continue
            entry['total'] += 1
            if is_delivered:
                entry['delivered'] += 1
            else:
                entry['in_progress'] += 1

    return stats

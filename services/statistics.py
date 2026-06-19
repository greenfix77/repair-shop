from typing import List, Dict


def update_statistics(repairs: List[Dict]) -> tuple:
    """Calculate statistics for repairs"""
    total = len(repairs)
    pending = len([r for r in repairs if r.get('status') == 'در انتظار'])
    in_progress = len([r for r in repairs if r.get('status') == 'در حال تعمیر'])
    completed = len([r for r in repairs if r.get('status') == 'تعمیر شده'])
    delivered = len([r for r in repairs if r.get('status') == 'تحویل داده شده'])
    
    return total, pending, in_progress, completed, delivered
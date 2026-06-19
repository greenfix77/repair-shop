from typing import List, Dict
from services.calculations import calculate_invoice


def build_table_rows(repairs: List[Dict]) -> List[Dict]:
    """
    Build table row data from repairs list.
    Returns a list of dictionaries containing all necessary data for table display.
    """
    rows_data = []
    
    for repair in repairs:
        # Extract and prepare data
        repair_id = str(repair['id'])
        customer_name = repair.get('customer_name', '')
        phone = repair.get('phone', '')
        brand = repair.get('brand', '')
        model = repair.get('model', '')
        issue = repair.get('issue', '')
        
        # Truncate issue if too long
        if len(issue) > 30:
            issue = issue[:30] + "..."
        
        status = repair.get('status', '')
        receive_date = repair.get('receive_date', '')
        delivery_date = repair.get('delivery_date', '')
        
        # Calculate financial totals
        parts = repair.get('parts_cost', 0)
        labor = repair.get('labor_cost', 0)
        tax = repair.get('tax', 0)
        discount = repair.get('discount', 0)
        
        subtotal, tax_amount, total = calculate_invoice(parts, labor, tax, discount)
        
        row_data = {
            'id': repair_id,
            'customer_name': customer_name,
            'phone': phone,
            'brand': brand,
            'model': model,
            'issue': issue,
            'status': status,
            'receive_date': receive_date,
            'delivery_date': delivery_date,
            'total_cost': f"{int(total):,}",
            'status_value': status,  # Raw status for UI styling
            'total_value': int(total)  # Raw total for UI styling
        }
        
        rows_data.append(row_data)
    
    return rows_data
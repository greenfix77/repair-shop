from core.storage.sqlite_storage import SQLiteStorage


def main():
    storage = SQLiteStorage()

    sample = [
        {
            'id': 1,
            'customer_name': 'test customer',
            'phone': '09120000000',
            'brand': 'dell',
            'model': 'xps 13',
            'issue': 'no power',
            'parts_cost': 500000,
            'labor_cost': 200000,
            'tax': 0.0,
            'discount': 0,
            'status': 'در انتظار',
            'receive_date': '1404/01/01',
            'delivery_date': '1404/01/05',
            'notes': '',
            'warranty': '1 ماه',
        },
        {
            'id': 2,
            'customer_name': 'another customer',
            'phone': '09121111111',
            'brand': 'hp',
            'model': 'pavilion',
            'issue': 'screen broken',
            'parts_cost': 1200000,
            'labor_cost': 300000,
            'tax': 9.0,
            'discount': 100000,
            'status': 'تکمیل شده',
            'receive_date': '1404/02/10',
            'delivery_date': '1404/02/15',
            'notes': 'گارانتی دارد',
            'warranty': '6 ماه',
        },
    ]

    storage.save_all(sample)
    loaded = storage.load_all()
    print(f"Loaded {len(loaded)} repairs from database:")

    for r in loaded:
        status_ok = bool(r['status'])
        print(f"  #{r['id']} - {r['customer_name']} - {r['brand']} {r['model']} - status_ok={status_ok}")


if __name__ == '__main__':
    main()

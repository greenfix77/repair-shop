from core.storage.init_db import init_database
from core.storage.repairs_storage import RepairsStorage
from core.storage.sqlite_storage import SQLiteStorage


def migrate_json_to_sqlite():
    init_database()

    json_storage = RepairsStorage()
    repairs = json_storage.load_all()

    sqlite_storage = SQLiteStorage()
    sqlite_storage.save_all(repairs)

    print(f"Migration completed.")
    print(f"Imported {len(repairs)} repairs.")


if __name__ == "__main__":
    migrate_json_to_sqlite()

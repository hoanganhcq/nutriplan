from app.db.database import get_connection
from app.services.vietfood import import_catalog

if __name__ == "__main__":
    with get_connection() as db:
        count = import_catalog(db)
    print(f"VietFood catalog ready: {count} foods")

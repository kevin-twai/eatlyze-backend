# scripts/run_cleanup_once.py
import asyncio
from app.db.session import get_db
from app.services.blacklist_cleanup import cleanup_expired_blacklist

async def main():
    agen = get_db()
    db = await agen.__anext__()
    try:
        deleted = await cleanup_expired_blacklist(db)
        await db.commit()
        print({"deleted": deleted})
    finally:
        try:
            await agen.aclose()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())

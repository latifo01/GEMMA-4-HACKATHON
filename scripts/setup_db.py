import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.backend.config import get_settings
from apps.backend.database import create_database


async def main() -> None:
    settings = get_settings()
    await create_database(settings)
    print(f"Database initialized at {settings.db_path}")


if __name__ == "__main__":
    asyncio.run(main())

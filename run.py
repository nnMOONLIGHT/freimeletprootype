"""Запуск платформы Фреймлёт."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from database import init_db
from app import app

if __name__ == "__main__":
    init_db()
    print("Фреймлёт: http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)

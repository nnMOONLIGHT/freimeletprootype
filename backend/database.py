"""SQLite-хранилище платформы."""

import sqlite3
import json
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "freimelet.db"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            region TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'school',
            directions TEXT DEFAULT '[]',
            consent_file TEXT,
            parent_consent TEXT DEFAULT 'pending',
            points INTEGER DEFAULT 50,
            works_count INTEGER DEFAULT 0,
            challenges_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS works (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            direction TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'moderation',
            views INTEGER DEFAULT 0,
            points INTEGER DEFAULT 10,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS ai_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            image_path TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            points INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS video_feed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            platform TEXT NOT NULL,
            embed_url TEXT NOT NULL,
            direction TEXT NOT NULL,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0
        );
        """
    )
    _seed_videos(c)
    _seed_demo(c)
    conn.commit()
    conn.close()


def _seed_demo(c):
    n = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if n:
        return
    from werkzeug.security import generate_password_hash

    demos = [
        ("demo@freimelet.ru", "demo123", "Алекс К.", 16, "Екатеринбург", "school", '["design","fashion","3d"]', "confirmed", 740, 18, 7),
        ("eva@freimelet.ru", "demo123", "Ева К.", 17, "Санкт-Петербург", "school", '["design"]', "confirmed", 1240, 22, 9),
        ("mila@freimelet.ru", "demo123", "Мила С.", 14, "Казань", "school", '["craft","text"]', "confirmed", 410, 8, 3),
    ]
    ids = []
    for row in demos:
        c.execute(
            """INSERT INTO users (email, password_hash, full_name, age, region, role, directions, parent_consent, points, works_count, challenges_count)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (row[0], generate_password_hash(row[1]), row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10]),
        )
        ids.append(c.execute("SELECT last_insert_rowid()").fetchone()[0])

    works = [
        (ids[0], "Кастомизация куртки «Новая форма»", "fashion", "Handmade, аппликация, вышивка", "published", 2340),
        (ids[1], "Шрифтовой постер «Волга»", "design", "Типографика для городского фестиваля", "published", 764),
        (ids[0], "Минималистичный стул", "design", "Эскиз + макет в Figma", "published", 312),
        (ids[2], "Сумка из переработанного текстиля", "craft", "Upcycle джинсов", "published", 198),
        (ids[1], "Звуковой портрет города", "text", "Ambient + field recording", "published", 540),
        (ids[0], "Мини-документалка «Двор»", "media", "60 сек, вертикаль", "published", 1120),
    ]
    for w in works:
        c.execute(
            "INSERT INTO works (user_id, title, direction, description, status, views) VALUES (?,?,?,?,?,?)",
            w,
        )


def _seed_videos(c):
    count = c.execute("SELECT COUNT(*) FROM video_feed").fetchone()[0]
    if count:
        return
    videos = [
        ("Кастомизация куртки за 60 сек", "@craft_ekb", "VK Видео", "https://vk.com/video_ext.php?oid=-123456&id=456789", "fashion", 12400, 890),
        ("Типографика для начинающих", "DesignDaily", "YouTube", "https://www.youtube.com/embed/aqz-KE-bpKQ", "design", 45200, 2100),
        ("3D-персонаж в Blender", "PolyLab", "YouTube", "https://www.youtube.com/embed/ScMzIvxBSi4", "3d", 33100, 1540),
        ("Керамика: первый горшок", "Гончарная мастерская", "RuTube", "https://rutube.ru/play/embed/00000000000000000000000000000000/", "craft", 8700, 420),
        ("Съёмка на телефон: свет", "PhotoSchool", "YouTube", "https://www.youtube.com/embed/aqz-KE-bpKQ", "media", 28900, 980),
        ("Beatmaking за 5 минут", "LoFi Studio", "YouTube", "https://www.youtube.com/embed/jfKfPfyJRdk", "text", 15600, 730),
        ("Upcycle: сумка из джинсов", "EcoCraft", "VK Видео", "https://vk.com/video_ext.php?oid=-654321&id=123456", "fashion", 9800, 560),
        ("Motion design intro", "MotionHub", "YouTube", "https://www.youtube.com/embed/1ZYbU82GVz4", "design", 22100, 1100),
    ]
    c.executemany(
        "INSERT INTO video_feed (title, author, platform, embed_url, direction, views, likes) VALUES (?,?,?,?,?,?,?)",
        videos,
    )


def create_user(data):
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO users (email, password_hash, full_name, age, region, role, directions, consent_file, parent_consent)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                data["email"].lower().strip(),
                generate_password_hash(data["password"]),
                data["full_name"].strip(),
                int(data["age"]),
                data["region"].strip(),
                data.get("role", "school"),
                json.dumps(data.get("directions", []), ensure_ascii=False),
                data.get("consent_file"),
                "pending" if int(data["age"]) < 18 else "confirmed",
            ),
        )
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO activities (user_id, action, detail, points) VALUES (?,?,?,?)",
            (uid, "Регистрация на платформе", None, 50),
        )
        conn.commit()
        return uid
    finally:
        conn.close()


def find_user(email):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email=?", (email.lower().strip(),)).fetchone()
    conn.close()
    return dict(row) if row else None


def verify_user(email, password):
    user = find_user(email)
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


def user_by_id(uid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_user(uid, **fields):
    conn = get_conn()
    allowed = {"directions", "parent_consent", "points", "works_count", "challenges_count"}
    parts, vals = [], []
    for k, v in fields.items():
        if k in allowed:
            parts.append(f"{k}=?")
            vals.append(v)
    if parts:
        vals.append(uid)
        conn.execute(f"UPDATE users SET {', '.join(parts)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def add_work(uid, title, direction, description=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO works (user_id, title, direction, description) VALUES (?,?,?,?)",
        (uid, title, direction, description),
    )
    conn.execute("UPDATE users SET works_count = works_count + 1, points = points + 10 WHERE id=?", (uid,))
    conn.execute(
        "INSERT INTO activities (user_id, action, detail, points) VALUES (?,?,?,?)",
        (uid, f"Опубликована работа «{title}»", direction, 10),
    )
    conn.commit()
    conn.close()


def list_works(limit=20):
    conn = get_conn()
    rows = conn.execute(
        """SELECT w.*, u.full_name, u.region, u.age FROM works w
           JOIN users u ON u.id = w.user_id
           ORDER BY w.created_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_analysis(uid, path, result):
    conn = get_conn()
    conn.execute(
        "INSERT INTO ai_analyses (user_id, image_path, result_json) VALUES (?,?,?)",
        (uid, path, json.dumps(result, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


def user_analyses(uid, limit=10):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM ai_analyses WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (uid, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def user_activities(uid):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM activities WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
        (uid,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_videos(direction=None):
    conn = get_conn()
    if direction and direction != "all":
        rows = conn.execute(
            "SELECT * FROM video_feed WHERE direction=? ORDER BY views DESC",
            (direction,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM video_feed ORDER BY views DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

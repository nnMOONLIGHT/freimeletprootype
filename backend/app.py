"""Сервер платформы Фреймлёт."""

import os
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.utils import secure_filename

from database import (
    init_db,
    create_user,
    verify_user,
    user_by_id,
    update_user,
    add_work,
    list_works,
    save_analysis,
    user_analyses,
    user_activities,
    list_videos,
)
from neural import StyleAnalyzer

BASE = Path(__file__).resolve().parent.parent
UPLOAD = BASE / "frontend" / "uploads"
STATIC = BASE / "frontend" / "static"

app = Flask(
    __name__,
    static_folder=str(STATIC),
    template_folder=str(BASE / "frontend" / "templates"),
)
app.secret_key = os.environ.get("FREIMELET_SECRET", "freimelet-dev-key-change-in-prod")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

ALLOWED = {"png", "jpg", "jpeg", "webp"}


def _ext_ok(name):
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED


def _current_user():
    uid = session.get("user_id")
    return user_by_id(uid) if uid else None


@app.route("/")
def index():
    return send_from_directory(BASE / "frontend" / "templates", "index.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory(STATIC, path)


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    required = ["email", "password", "full_name", "age", "region", "role"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Поле «{field}» обязательно"}), 400

    if len(data["password"]) < 6:
        return jsonify({"error": "Пароль — минимум 6 символов"}), 400

    try:
        uid = create_user(data)
    except Exception:
        return jsonify({"error": "Email уже занят"}), 409

    session["user_id"] = uid
    user = user_by_id(uid)
    return jsonify({"ok": True, "user": _public_user(user)})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    user = verify_user(data.get("email", ""), data.get("password", ""))
    if not user:
        return jsonify({"error": "Неверный email или пароль"}), 401
    session["user_id"] = user["id"]
    return jsonify({"ok": True, "user": _public_user(user)})


@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"ok": True})


@app.route("/api/me")
def me():
    user = _current_user()
    if not user:
        return jsonify({"user": None})
    return jsonify({
        "user": _public_user(user),
        "activities": user_activities(user["id"]),
        "analyses": [
            {**a, "result": __import__("json").loads(a["result_json"])}
            for a in user_analyses(user["id"], 5)
        ],
    })


@app.route("/api/profile/directions", methods=["POST"])
def set_directions():
    user = _current_user()
    if not user:
        return jsonify({"error": "Не авторизован"}), 401
    dirs = request.get_json(force=True).get("directions", [])
    import json
    update_user(user["id"], directions=json.dumps(dirs, ensure_ascii=False))
    return jsonify({"ok": True})


@app.route("/api/consent", methods=["POST"])
def consent():
    user = _current_user()
    if not user:
        return jsonify({"error": "Не авторизован"}), 401
    status = request.get_json(force=True).get("status", "confirmed")
    update_user(user["id"], parent_consent=status)
    return jsonify({"ok": True})


@app.route("/api/works", methods=["GET", "POST"])
def works():
    if request.method == "GET":
        return jsonify({"works": list_works()})

    user = _current_user()
    if not user:
        return jsonify({"error": "Не авторизован"}), 401
    if user["parent_consent"] == "pending" and user["age"] < 18:
        return jsonify({"error": "Нужно согласие родителя"}), 403

    data = request.get_json(force=True)
    add_work(user["id"], data["title"], data["direction"], data.get("description", ""))
    return jsonify({"ok": True})


@app.route("/api/ai/analyze", methods=["POST"])
def analyze():
    user = _current_user()
    if "photo" not in request.files:
        return jsonify({"error": "Нужен файл photo"}), 400

    f = request.files["photo"]
    if not f.filename or not _ext_ok(f.filename):
        return jsonify({"error": "Формат: JPG, PNG, WEBP"}), 400

    UPLOAD.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}_{secure_filename(f.filename)}"
    path = UPLOAD / name
    f.save(path)

    result = StyleAnalyzer.shared().analyze(str(path))
    if user:
        save_analysis(user["id"], name, result)

    return jsonify({"ok": True, "result": result, "preview": f"/uploads/{name}"})


@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOAD, filename)


@app.route("/api/videos")
def videos():
    direction = request.args.get("direction", "all")
    return jsonify({"videos": list_videos(direction)})


@app.route("/api/consent-template")
def consent_template():
    text = """СОГЛАСИЕ НА ОБРАБОТКУ ПЕРСОНАЛЬНЫХ ДАННЫХ
и участие несовершеннолетнего на платформе «Фреймлёт»

Я, ________________________________________________ (ФИО родителя/законного представителя),
даю согласие на обработку персональных данных моего ребёнка
________________________________________________ (ФИО ребёнка), возраст _____ лет,
для регистрации и участия на творческой платформе freimelet.ru.

Подпись: _________________   Дата: «___» __________ 20___ г.
"""
    return jsonify({"text": text})


def _public_user(u):
    import json
    return {
        "id": u["id"],
        "email": u["email"],
        "full_name": u["full_name"],
        "age": u["age"],
        "region": u["region"],
        "role": u["role"],
        "directions": json.loads(u["directions"] or "[]"),
        "parent_consent": u["parent_consent"],
        "points": u["points"],
        "works_count": u["works_count"],
        "challenges_count": u["challenges_count"],
    }


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

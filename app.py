"""
分学科教师需求填写系统 - Flask 后端
功能：提供教师需求数据的增删查 API，使用 SQLite 持久化存储
"""
import sqlite3
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "needs.db")


def get_db():
    """获取数据库连接，开启外键约束"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """初始化数据库表结构：submissions（提交记录）和 submission_items（需求明细）"""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS submission_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            tag TEXT NOT NULL,
            description TEXT NOT NULL,
            FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


@app.route("/")
def index():
    """渲染前端页面"""
    return render_template("index.html")


@app.route("/api/needs", methods=["GET"])
def get_needs():
    """获取所有教师需求，按提交时间倒序"""
    conn = get_db()
    submissions = conn.execute(
        "SELECT id, name, subject, created_at FROM submissions ORDER BY created_at DESC"
    ).fetchall()

    result = []
    for sub in submissions:
        items = conn.execute(
            "SELECT category, tag, description FROM submission_items WHERE submission_id = ?",
            (sub["id"],)
        ).fetchall()
        result.append({
            "id": sub["id"],
            "name": sub["name"],
            "subject": sub["subject"],
            "created_at": sub["created_at"],
            "items": [dict(row) for row in items]
        })
    conn.close()
    return jsonify(result)


@app.route("/api/needs", methods=["POST"])
def create_needs():
    """
    提交教师需求
    请求体 JSON：{ name, subject, items: [{ category, tag, description }] }
    至少需要选择一项需求
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求数据不能为空"}), 400

    name = data.get("name", "").strip()
    subject = data.get("subject", "").strip()
    items = data.get("items", [])

    if not name:
        return jsonify({"error": "请输入教师姓名"}), 400
    if not subject:
        return jsonify({"error": "请选择所属学科"}), 400
    if not items:
        return jsonify({"error": "请至少选择一项需求"}), 400

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO submissions (name, subject, created_at) VALUES (?, ?, ?)",
        (name, subject, created_at)
    )
    submission_id = cursor.lastrowid

    for item in items:
        conn.execute(
            "INSERT INTO submission_items (submission_id, category, tag, description) VALUES (?, ?, ?, ?)",
            (submission_id, item["category"], item["tag"], item["description"])
        )
    conn.commit()
    conn.close()

    return jsonify({"message": "提交成功", "id": submission_id}), 201


@app.route("/api/needs/<int:submission_id>", methods=["DELETE"])
def delete_needs(submission_id):
    """按 ID 删除指定提交记录及其关联的需求明细"""
    conn = get_db()
    cursor = conn.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
    conn.commit()
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "记录不存在"}), 404
    conn.close()
    return jsonify({"message": "删除成功"}), 200


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
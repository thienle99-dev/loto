import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
import json


# Đường dẫn file SQLite trong project
DB_PATH = Path(__file__).parent.parent / "loto.db"


def get_connection() -> sqlite3.Connection:
    """Tạo connection đến SQLite DB."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Khởi tạo các bảng cần thiết nếu chưa tồn tại."""
    conn = get_connection()
    cur = conn.cursor()

    # Lưu WheelSession theo chat_id, dạng JSON
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            chat_id INTEGER PRIMARY KEY,
            session_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    # Lưu thống kê leaderboard theo chat + user
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stats (
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL, -- 'wins' hoặc 'participations'
            count REAL NOT NULL,
            name TEXT,
            PRIMARY KEY (chat_id, user_id, type)
        )
        """
    )

    # Lưu kết quả game gần nhất theo chat
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS last_results (
            chat_id INTEGER PRIMARY KEY,
            data_json TEXT NOT NULL,
            saved_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


# ---------- Session ----------
def save_session(chat_id: int, session_dict: Dict[str, Any]) -> None:
    """Lưu (hoặc cập nhật) session cho một chat."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat(timespec="seconds")

    cur.execute(
        """
        INSERT INTO sessions(chat_id, session_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
            session_json = excluded.session_json,
            updated_at   = excluded.updated_at
        """,
        (chat_id, json.dumps(session_dict, ensure_ascii=False), now),
    )

    conn.commit()
    conn.close()


def load_session(chat_id: int) -> Optional[Dict[str, Any]]:
    """Tải session cho một chat, trả về dict hoặc None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT session_json FROM sessions WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return json.loads(row["session_json"])


def delete_session_row(chat_id: int) -> None:
    """Xoá session của một chat khỏi DB."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()


# ---------- Stats ----------
def save_stats(chat_id: int, chat_stats: Dict[str, Dict[int, Dict[str, Any]]]) -> None:
    """
    Lưu thống kê cho một chat.

    chat_stats format giống biến global `stats[chat_id]` hiện tại:
      {
        "wins": { user_id: {"count": float, "name": str}, ... },
        "participations": { user_id: {"count": float, "name": str}, ... }
      }
    """
    conn = get_connection()
    cur = conn.cursor()

    wins = chat_stats.get("wins", {})
    participations = chat_stats.get("participations", {})

    # Xoá dữ liệu cũ của chat này
    cur.execute("DELETE FROM stats WHERE chat_id = ?", (chat_id,))

    for user_id, info in wins.items():
        cur.execute(
            """
            INSERT INTO stats(chat_id, user_id, type, count, name)
            VALUES (?, ?, 'wins', ?, ?)
            """,
            (chat_id, int(user_id), float(info.get("count", 0.0)), info.get("name")),
        )

    for user_id, info in participations.items():
        cur.execute(
            """
            INSERT INTO stats(chat_id, user_id, type, count, name)
            VALUES (?, ?, 'participations', ?, ?)
            """,
            (chat_id, int(user_id), float(info.get("count", 0.0)), info.get("name")),
        )

    conn.commit()
    conn.close()


def load_stats(chat_id: int) -> Dict[str, Dict[int, Dict[str, Any]]]:
    """Tải thống kê cho một chat, trả về dict cùng format với `stats[chat_id]`."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, type, count, name FROM stats WHERE chat_id = ?",
        (chat_id,),
    )
    rows = cur.fetchall()
    conn.close()

    wins: Dict[int, Dict[str, Any]] = {}
    participations: Dict[int, Dict[str, Any]] = {}

    for r in rows:
        target = wins if r["type"] == "wins" else participations
        uid = int(r["user_id"])
        target[uid] = {
            "count": float(r["count"]),
            "name": r["name"],
        }

    return {"wins": wins, "participations": participations}


# ---------- Last result ----------
def save_last_result(chat_id: int, data: Dict[str, Any]) -> None:
    """Lưu kết quả game gần nhất cho một chat."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat(timespec="seconds")

    cur.execute(
        """
        INSERT INTO last_results(chat_id, data_json, saved_at)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
            data_json = excluded.data_json,
            saved_at  = excluded.saved_at
        """,
        (chat_id, json.dumps(data, ensure_ascii=False), now),
    )

    conn.commit()
    conn.close()


def load_last_result(chat_id: int) -> Optional[Dict[str, Any]]:
    """Tải kết quả game gần nhất của một chat."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT data_json FROM last_results WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return json.loads(row["data_json"])


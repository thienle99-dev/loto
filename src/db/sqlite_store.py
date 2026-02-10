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
            username TEXT,
            PRIMARY KEY (chat_id, user_id, type)
        )
        """
    )

    # Cập nhật table stats nếu thiếu cột username (migration)
    try:
        cur.execute("ALTER TABLE stats ADD COLUMN username TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass # Cột đã tồn tại

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
    Lưu thống kê cho một chat bằng Transaction để tối ưu cực độ.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Bắt đầu transaction
        cur.execute("BEGIN TRANSACTION")

        # Xoá dữ liệu cũ của chat này
        cur.execute("DELETE FROM stats WHERE chat_id = ?", (chat_id,))

        # Chuẩn bị dữ liệu cho executemany
        data_to_insert = []
        
        wins = chat_stats.get("wins", {})
        for user_id, info in wins.items():
            data_to_insert.append((chat_id, int(user_id), 'wins', float(info.get("count", 0.0)), info.get("name"), info.get("username")))

        participations = chat_stats.get("participations", {})
        for user_id, info in participations.items():
            data_to_insert.append((chat_id, int(user_id), 'participations', float(info.get("count", 0.0)), info.get("name"), info.get("username")))

        if data_to_insert:
            cur.executemany(
                """
                INSERT INTO stats(chat_id, user_id, type, count, name, username)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                data_to_insert
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def load_stats(chat_id: int) -> Dict[str, Dict[int, Dict[str, Any]]]:
    """Tải thống kê cho một chat, trả về dict cùng format với `stats[chat_id]`."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, type, count, name, username FROM stats WHERE chat_id = ?",
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
            "username": r["username"],
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


# ---------- Photo Cache ----------
def save_photo_cache(ticket_code: str, file_id: str) -> None:
    """Lưu file_id của ảnh vé vào cache."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat(timespec="seconds")
    
    cur.execute(
        """
        INSERT INTO photo_cache(ticket_code, file_id, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(ticket_code) DO UPDATE SET
            file_id = excluded.file_id,
            updated_at = excluded.updated_at
        """,
        (ticket_code, file_id, now),
    )
    conn.commit()
    conn.close()

def get_photo_cache(ticket_code: str) -> Optional[str]:
    """Lấy file_id từ cache nếu có."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT file_id FROM photo_cache WHERE ticket_code = ?", (ticket_code,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return row["file_id"]
    return None



# ---------- Video Note Cache ----------
def save_video_note_cache(number: int, file_id: str) -> None:
    """Lưu file_id của video note vào cache."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat(timespec="seconds")
    
    cur.execute(
        """
        INSERT INTO video_note_cache(number, file_id, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(number) DO UPDATE SET
            file_id = excluded.file_id,
            updated_at = excluded.updated_at
        """,
        (number, file_id, now),
    )
    conn.commit()
    conn.close()

def get_video_note_cache(number: int) -> Optional[str]:
    """Lấy file_id từ cache nếu có."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT file_id FROM video_note_cache WHERE number = ?", (number,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return row["file_id"]
    return None


# ---------- Admin ----------
def get_all_users() -> list[dict]:
    """Lấy danh sách tất cả user từng tham gia (kèm chat_id)."""
    conn = get_connection()
    cur = conn.cursor()
    # Lấy user_id, name và chat_id từ stats. 
    # Một user có thể tham gia nhiều chat, ta lấy tất cả các cặp (chat, user).
    cur.execute(
        """
        SELECT chat_id, user_id, name 
        FROM stats 
        WHERE type = 'wins'
        GROUP BY chat_id, user_id
        """
    )
    rows = cur.fetchall()
    conn.close()
    
    return [{"chat_id": r["chat_id"], "user_id": r["user_id"], "name": r["name"]} for r in rows]

def update_user_token(chat_id: int, user_id: int, amount: float) -> bool:
    """Cập nhật token cho một user trong một chat cụ thể."""
    conn = get_connection()
    cur = conn.cursor()
    
    # Kiểm tra xem bản ghi có tồn tại không
    cur.execute(
        "SELECT 1 FROM stats WHERE chat_id = ? AND user_id = ? AND type = 'wins'",
        (chat_id, user_id)
    )
    exists = cur.fetchone()
    
    if exists:
        cur.execute(
            "UPDATE stats SET count = ? WHERE chat_id = ? AND user_id = ? AND type = 'wins'",
            (amount, chat_id, user_id)
        )
    else:
        # Nếu chưa có bản ghi 'wins', tạo mới
        # Cần tìm name từ participations nếu có
        cur.execute(
            "SELECT name FROM stats WHERE chat_id = ? AND user_id = ? LIMIT 1",
            (chat_id, user_id)
        )
        row = cur.fetchone()
        name = row["name"] if row else str(user_id)
        
        cur.execute(
            "INSERT INTO stats (chat_id, user_id, type, count, name) VALUES (?, ?, 'wins', ?, ?)",
            (chat_id, user_id, amount, name)
        )
        
    conn.commit()
    conn.close()
    return True

def get_unique_groups() -> list[int]:
    """Lấy danh sách các unique chat_id từ bảng stats."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT chat_id FROM stats")
    rows = cur.fetchall()
    conn.close()
    return [r["chat_id"] for r in rows]

def get_user_id_by_username(chat_id: int, username: str) -> Optional[int]:
    """Tìm user_id từ username trong một chat cụ thể."""
    username = username.lstrip('@').lower()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id FROM stats WHERE chat_id = ? AND LOWER(username) = ? LIMIT 1",
        (chat_id, username)
    )
    row = cur.fetchone()
    conn.close()
    return row["user_id"] if row else None

def get_total_users_count() -> int:
    """Đếm tổng số user duy nhất trong DB."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT user_id) as count FROM stats")
    row = cur.fetchone()
    conn.close()
    return row["count"] if row else 0

def get_total_groups_count() -> int:
    """Đếm tổng số nhóm duy nhất trong DB."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT chat_id) as count FROM stats")
    row = cur.fetchone()
    conn.close()
    return row["count"] if row else 0

def get_unique_groups() -> list[int]:
    """Lấy danh sách chat_id duy nhất từ stats và sessions."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT chat_id FROM stats UNION SELECT DISTINCT chat_id FROM sessions")
    rows = cur.fetchall()
    conn.close()
    return [row["chat_id"] for row in rows]

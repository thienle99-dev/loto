"""
Quản lý wheel sessions cho Telegram bot (theo từng chat).

Session được lưu trong bộ nhớ và có thể đồng bộ xuống SQLite thông qua
`src.db.sqlite_store`.
"""
from typing import Dict, Optional
from ..models.wheel_session import WheelSession
from src.db.sqlite_store import load_session, save_session, delete_session_row


class SessionManager:
    """Quản lý wheel sessions cho nhiều chat"""
    
    def __init__(self):
        # Key: chat_id, Value: WheelSession
        self._sessions: Dict[int, WheelSession] = {}

    def get_session(self, chat_id: int) -> Optional[WheelSession]:
        """
        Lấy session của một chat.
        Ưu tiên lấy từ cache RAM, nếu không có thì thử load từ SQLite.
        """
        session = self._sessions.get(chat_id)
        if session:
            return session

        data = load_session(chat_id)
        if not data:
            return None

        session = WheelSession.from_dict(data)
        self._sessions[chat_id] = session
        return session

    def create_session(
        self,
        chat_id: int,
        start: int,
        end: int,
        remove_after_spin: bool = True,
    ) -> WheelSession:
        """Tạo session mới cho một chat và lưu xuống SQLite."""
        from ..bot.wheel import create_wheel_session

        session = create_wheel_session(start, end, remove_after_spin)
        self._sessions[chat_id] = session
        save_session(chat_id, session.to_dict())
        return session

    def delete_session(self, chat_id: int) -> bool:
        """Xóa session của một chat (cả RAM lẫn DB)."""
        if chat_id in self._sessions:
            del self._sessions[chat_id]
        delete_session_row(chat_id)
        return True

    def has_session(self, chat_id: int) -> bool:
        """Kiểm tra chat có session không."""
        return self.get_session(chat_id) is not None

    def persist_session(self, chat_id: int) -> None:
        """Lưu lại session của chat hiện tại xuống SQLite."""
        session = self._sessions.get(chat_id)
        if session is not None:
            save_session(chat_id, session.to_dict())

    def clear_all(self) -> None:
        """Xóa tất cả sessions trong RAM (không đụng tới DB)."""
        self._sessions.clear()

    def get_sessions_containing_user(self, user_id: int) -> list[tuple[int, WheelSession]]:
        """Lấy danh sách (chat_id, session) mà user_id đang tham gia"""
        results = []
        for chat_id, session in self._sessions.items():
            # Chỉ check session active
            if not getattr(session, "started", False):
                continue
                
            # Check owner
            if getattr(session, "owner_id", None) == user_id:
                results.append((chat_id, session))
                continue
                
            # Check participants
            participants = getattr(session, "participants", [])
            for p in participants:
                if p.get("user_id") == user_id:
                    results.append((chat_id, session))
                    break
        return results

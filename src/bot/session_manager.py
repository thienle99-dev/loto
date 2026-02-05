"""
Quản lý user sessions cho Telegram bot
"""
from typing import Dict, Optional
from ..models.wheel_session import WheelSession


class SessionManager:
    """Quản lý wheel sessions cho nhiều users"""
    
    def __init__(self):
        self._sessions: Dict[int, WheelSession] = {}
    
    def get_session(self, user_id: int) -> Optional[WheelSession]:
        """Lấy session của user"""
        return self._sessions.get(user_id)
    
    def create_session(
        self,
        user_id: int,
        start: int,
        end: int,
        remove_after_spin: bool = True
    ) -> WheelSession:
        """Tạo session mới cho user"""
        from ..bot.wheel import create_wheel_session
        
        session = create_wheel_session(start, end, remove_after_spin)
        self._sessions[user_id] = session
        return session
    
    def delete_session(self, user_id: int) -> bool:
        """Xóa session của user"""
        if user_id in self._sessions:
            del self._sessions[user_id]
            return True
        return False
    
    def has_session(self, user_id: int) -> bool:
        """Kiểm tra user có session không"""
        return user_id in self._sessions
    
    def clear_all(self):
        """Xóa tất cả sessions"""
        self._sessions.clear()

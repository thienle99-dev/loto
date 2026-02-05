"""
Model quản lý session của random wheel
"""
from datetime import datetime
from typing import List, Optional
import json
import uuid


class WheelSession:
    """Quản lý một session quay wheel"""
    
    def __init__(
        self,
        start_number: int,
        end_number: int,
        remove_after_spin: bool = True,
        session_id: Optional[str] = None,
        game_name: Optional[str] = None,
        owner_id: Optional[int] = None,
    ):
        """
        Khởi tạo wheel session
        
        Args:
            start_number: Số bắt đầu (x)
            end_number: Số kết thúc (y)
            remove_after_spin: Có loại bỏ số sau khi quay không
            session_id: ID của session (tự động tạo nếu None)
            game_name: Tên game (tuỳ chọn)
            owner_id: ID người tạo session (tuỳ chọn)
        """
        if start_number > end_number:
            raise ValueError("start_number phải nhỏ hơn hoặc bằng end_number")
        
        if start_number < 0:
            raise ValueError("start_number phải >= 0")
        
        # Giới hạn số lượng số trong danh sách
        max_numbers = 90
        if (end_number - start_number + 1) > max_numbers:
            raise ValueError(f"Khoảng số quá lớn. Tối đa {max_numbers} số")
        
        self.id = session_id or str(uuid.uuid4())
        self.start_number = start_number
        self.end_number = end_number
        self.remove_after_spin = remove_after_spin
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        # Thông tin meta cho game/session
        self.game_name = game_name
        self.owner_id = owner_id
        # Danh sách người tham gia game: [{user_id, name}, ...]
        self.participants: list[dict] = []
        # Trạng thái game đã bắt đầu hay chưa (host dùng /startsession)
        self.started: bool = False
        
        # Tạo danh sách số ban đầu
        self.available_numbers = list(range(start_number, end_number + 1))
        self.removed_numbers = []
        self.last_spin: Optional[int] = None
        self.spin_count = 0
        # Lịch sử các lần quay: [{'number': int, 'time': str}, ...]
        self.history: list[dict] = []
    
    def get_total_numbers(self) -> int:
        """Trả về tổng số số ban đầu"""
        return self.end_number - self.start_number + 1
    
    def get_remaining_count(self) -> int:
        """Trả về số lượng số còn lại"""
        return len(self.available_numbers)
    
    def get_removed_count(self) -> int:
        """Trả về số lượng số đã loại bỏ"""
        return len(self.removed_numbers)
    
    def is_empty(self) -> bool:
        """Kiểm tra danh sách số còn lại có rỗng không"""
        return len(self.available_numbers) == 0
    
    def to_dict(self) -> dict:
        """Chuyển đổi session thành dictionary"""
        return {
            'id': self.id,
            'start_number': self.start_number,
            'end_number': self.end_number,
            'remove_after_spin': self.remove_after_spin,
            'available_numbers': self.available_numbers,
            'removed_numbers': self.removed_numbers,
            'last_spin': self.last_spin,
            'spin_count': self.spin_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'history': self.history,
            'game_name': self.game_name,
            'owner_id': self.owner_id,
            'participants': self.participants,
            'started': self.started,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WheelSession':
        """Tạo WheelSession từ dictionary"""
        session = cls(
            start_number=data['start_number'],
            end_number=data['end_number'],
            remove_after_spin=data.get('remove_after_spin', True),
            session_id=data.get('id'),
            game_name=data.get('game_name'),
            owner_id=data.get('owner_id'),
        )
        session.available_numbers = data.get('available_numbers', session.available_numbers)
        session.removed_numbers = data.get('removed_numbers', [])
        session.last_spin = data.get('last_spin')
        session.spin_count = data.get('spin_count', 0)
        session.created_at = datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        session.updated_at = datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        session.history = data.get('history', [])
        session.participants = data.get('participants', [])
        session.started = data.get('started', False)
        return session

    # Quản lý người tham gia
    def add_participant(self, user_id: int, name: str) -> bool:
        """Thêm người chơi vào danh sách tham gia. Trả về True nếu thêm mới, False nếu đã tồn tại."""
        for p in self.participants:
            if p.get("user_id") == user_id:
                # Cập nhật tên nếu đổi
                p["name"] = name
                return False
        self.participants.append({"user_id": user_id, "name": name})
        self.updated_at = datetime.now()
        return True

    def remove_participant(self, user_id: int) -> bool:
        """Xoá người chơi khỏi danh sách tham gia. Trả về True nếu xoá được."""
        before = len(self.participants)
        self.participants = [p for p in self.participants if p.get("user_id") != user_id]
        if len(self.participants) != before:
            self.updated_at = datetime.now()
            return True
        return False

    def get_participants(self) -> list[dict]:
        """Trả về danh sách người tham gia hiện tại."""
        return list(self.participants)

    def get_recent_history(self, limit: int = 10) -> list[dict]:
        """Trả về lịch sử quay gần đây (mặc định 10 lần gần nhất)"""
        if limit <= 0:
            return []
        return self.history[-limit:]
    
    def __repr__(self) -> str:
        return (
            f"WheelSession(id={self.id}, "
            f"range={self.start_number}-{self.end_number}, "
            f"remaining={self.get_remaining_count()}/{self.get_total_numbers()})"
        )

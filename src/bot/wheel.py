"""
Core logic cho random wheel bot
"""
import random
from typing import Optional
from datetime import datetime
from ..models.wheel_session import WheelSession


def create_wheel_session(
    start: int,
    end: int,
    remove_after_spin: bool = True
) -> WheelSession:
    """
    Tạo một wheel session mới
    
    Args:
        start: Số bắt đầu (x)
        end: Số kết thúc (y)
        remove_after_spin: Có loại bỏ số sau khi quay không
    
    Returns:
        WheelSession object
    
    Raises:
        ValueError: Nếu input không hợp lệ
    """
    return WheelSession(
        start_number=start,
        end_number=end,
        remove_after_spin=remove_after_spin
    )


def spin_wheel(session: WheelSession) -> int:
    """
    Quay wheel và chọn ngẫu nhiên một số
    
    Args:
        session: WheelSession object
    
    Returns:
        Số được chọn ngẫu nhiên
    
    Raises:
        ValueError: Nếu danh sách số còn lại rỗng
    """
    if session.is_empty():
        raise ValueError("Danh sách số đã hết! Vui lòng reset để tiếp tục.")
    
    # Chọn ngẫu nhiên một số
    selected_number = random.choice(session.available_numbers)
    
    # Loại bỏ số nếu remove_after_spin = True
    if session.remove_after_spin:
        session.available_numbers.remove(selected_number)
        session.removed_numbers.append(selected_number)
    
    # Cập nhật thông tin
    session.last_spin = selected_number
    session.spin_count += 1
    session.updated_at = datetime.now()
    # Lưu lịch sử quay
    session.history.append(
        {
            "number": selected_number,
            "time": datetime.now().isoformat(timespec="seconds"),
        }
    )
    # Giới hạn lịch sử để tránh phình bộ nhớ
    if len(session.history) > 1000:
        session.history.pop(0)
    
    return selected_number


def reset_session(session: WheelSession) -> WheelSession:
    """
    Reset session về trạng thái ban đầu
    
    Args:
        session: WheelSession object
    
    Returns:
        WheelSession object đã được reset
    """
    # Khôi phục danh sách số
    session.available_numbers = list(range(session.start_number, session.end_number + 1))
    session.removed_numbers = []
    session.last_spin = None
    session.spin_count = 0
    session.updated_at = __import__('datetime').datetime.now()
    
    return session


def set_remove_mode(session: WheelSession, remove: bool) -> WheelSession:
    """
    Thay đổi chế độ loại bỏ số sau khi quay
    
    Args:
        session: WheelSession object
        remove: True nếu muốn loại bỏ, False nếu không
    
    Returns:
        WheelSession object đã được cập nhật
    """
    session.remove_after_spin = remove
    session.updated_at = __import__('datetime').datetime.now()
    
    return session


def get_session_status(session: WheelSession) -> dict:
    """
    Lấy thông tin trạng thái của session
    
    Args:
        session: WheelSession object
    
    Returns:
        Dictionary chứa thông tin trạng thái
    """
    return {
        'session_id': session.id,
        'range': f"{session.start_number} -> {session.end_number}",
        'total_numbers': session.get_total_numbers(),
        'remaining_count': session.get_remaining_count(),
        'removed_count': session.get_removed_count(),
        'remove_after_spin': session.remove_after_spin,
        'last_spin': session.last_spin,
        'spin_count': session.spin_count,
        'is_empty': session.is_empty()
    }


def clear_session(session: WheelSession) -> None:
    """
    Xóa toàn bộ dữ liệu session (giữ lại cấu trúc)
    
    Args:
        session: WheelSession object
    """
    session.available_numbers = []
    session.removed_numbers = []
    session.last_spin = None
    session.spin_count = 0
    session.updated_at = __import__('datetime').datetime.now()

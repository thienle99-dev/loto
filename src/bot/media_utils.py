import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Thư mục lưu trữ media
BASE_DIR = Path(__file__).parent.parent.parent
VIDEO_NOTES_DIR = BASE_DIR / "video_notes"

def ensure_dirs():
    """Đảm bảo các thư mục media tồn tại"""
    if not VIDEO_NOTES_DIR.exists():
        VIDEO_NOTES_DIR.mkdir(parents=True, exist_ok=True)

def get_video_note_file(number: int) -> str:
    """Lấy file video tròn (.mp4) nếu có"""
    ensure_dirs()
    # Tìm file có tên số (ví dụ: 10.mp4 hoặc so_10.mp4)
    possible_names = [f"{number}.mp4", f"so_{number}.mp4"]
    for name in possible_names:
        file_path = VIDEO_NOTES_DIR / name
        if file_path.exists():
            return str(file_path)
    return None

import os
import logging
from pathlib import Path
from gtts import gTTS

logger = logging.getLogger(__name__)

# Thư mục lưu trữ media
BASE_DIR = Path(__file__).parent.parent.parent
VOICE_CACHE_DIR = BASE_DIR / "voice_cache"
VIDEO_NOTES_DIR = BASE_DIR / "video_notes"

def ensure_dirs():
    """Đảm bảo các thư mục media tồn tại"""
    for d in [VOICE_CACHE_DIR, VIDEO_NOTES_DIR]:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)

def get_voice_calling_file(number: int) -> str:
    """Tạo hoặc lấy file âm thanh gọi số (.mp3)"""
    ensure_dirs()
    file_path = VOICE_CACHE_DIR / f"so_{number}.mp3"
    
    if file_path.exists():
        return str(file_path)
    
    try:
        text = f"Số {number}"
        tts = gTTS(text=text, lang='vi')
        tts.save(str(file_path))
        return str(file_path)
    except Exception as e:
        logger.error(f"Lỗi khi tạo voice cho số {number}: {e}")
        return None

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

import os
import logging
from pathlib import Path
from gtts import gTTS

logger = logging.getLogger(__name__)

# Thư mục lưu cache âm thanh
VOICE_CACHE_DIR = Path(__file__).parent.parent.parent / "voice_cache"

def ensure_cache_dir():
    """Đảm bảo thư mục cache tồn tại"""
    if not VOICE_CACHE_DIR.exists():
        VOICE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_voice_calling_file(number: int) -> str:
    """
    Tạo hoặc lấy file âm thanh gọi số.
    Trả về đường dẫn tuyệt đối đến file .mp3
    """
    ensure_cache_dir()
    file_path = VOICE_CACHE_DIR / f"so_{number}.mp3"
    
    if file_path.exists():
        return str(file_path)
    
    try:
        # Tạo câu gọi số: "Số 10"
        text = f"Số {number}"
        tts = gTTS(text=text, lang='vi')
        tts.save(str(file_path))
        return str(file_path)
    except Exception as e:
        logger.error(f"Lỗi khi tạo voice cho số {number}: {e}")
        return None

import logging
import time
from typing import Dict

logger = logging.getLogger(__name__)

class IdempotencyManager:
    """Quản lý và loại bỏ các update trùng lặp từ Telegram"""
    def __init__(self, ttl_seconds: int = 3600):
        # {update_id: timestamp}
        self._processed_updates: Dict[int, float] = {}
        self.ttl = ttl_seconds
        self._last_cleanup = time.time()

    def is_duplicate(self, update_id: int) -> bool:
        """Kiểm tra xem Update ID này đã được xử lý chưa"""
        now = time.time()
        
        # Thỉnh thoảng dọn dẹp cache
        if now - self._last_cleanup > 300: # 5 phút dọn 1 lần
            self._cleanup(now)

        if update_id in self._processed_updates:
            # logger.debug(f"Duplicate update detected: {update_id}")
            return True
        
        # Đánh dấu là đã xử lý
        self._processed_updates[update_id] = now
        return False

    def _cleanup(self, now: float):
        """Xóa các bản ghi cũ hơn TTL"""
        expired = [uid for uid, ts in self._processed_updates.items() if now - ts > self.ttl]
        for uid in expired:
            del self._processed_updates[uid]
        self._last_cleanup = now
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired update IDs from idempotency cache")

# Global instance
idempotency_manager = IdempotencyManager()

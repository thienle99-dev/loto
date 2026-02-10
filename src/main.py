"""
Main entry point cho Telegram bot
"""
import sys
import os
from pathlib import Path

# Thêm thư mục gốc vào PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import logging
from datetime import datetime
from config.config import TELEGRAM_BOT_TOKEN
from src.bot.telegram_bot import setup_bot
from src.db.sqlite_store import init_db

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Start time for uptime calculation
bot_start_time = datetime.now()


def main():
    """Main function"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN không được tìm thấy!")
        logger.error("Vui lòng tạo file .env và thêm TELEGRAM_BOT_TOKEN=your_token")
        return
    
    logger.info("Đang khởi động bot...")

    # Khởi tạo database (nếu chưa có)
    init_db()

    # Khôi phục các ván game đang hoạt động từ DB vào RAM
    # (Hiện tại bot tự động khôi phục session khi cần thông thông qua session_manager nếu call)
    # Nhưng ta giữ logic init_db
    
    # Setup bot
    application = setup_bot(TELEGRAM_BOT_TOKEN)
    
    # Run bot
    logger.info("Bot đã sẵn sàng!")
    application.run_polling()


if __name__ == "__main__":
    main()

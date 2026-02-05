"""
Main entry point cho Telegram bot
"""
import sys
import os
from pathlib import Path

# Thêm thư mục gốc vào PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import asyncio
import logging
from config.config import TELEGRAM_BOT_TOKEN
from src.bot.telegram_bot import setup_bot

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Main function"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN không được tìm thấy!")
        logger.error("Vui lòng tạo file .env và thêm TELEGRAM_BOT_TOKEN=your_token")
        return
    
    logger.info("Đang khởi động bot...")
    
    # Setup bot
    application = setup_bot(TELEGRAM_BOT_TOKEN)
    
    # Run bot
    logger.info("Bot đã sẵn sàng!")
    application.run_polling()


if __name__ == "__main__":
    main()

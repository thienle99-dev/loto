import functools
import logging
from src.bot.queue_manager import queue_manager

logger = logging.getLogger(__name__)

def queued_handler(func):
    """
    Decorator để biến một handler truyền thống thành Producer.
    Handler sẽ đẩy công việc vào hàng đợi và trả về ngay lập tức.
    """
    @functools.wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        chat_id = update.effective_chat.id if update.effective_chat else 0
        user_id = update.effective_user.id if update.effective_user else 0
        
        # logger.info(f"Queuing request from {user_id} in chat {chat_id}: {func.__name__}")
        
        # Đẩy vào queue xử lý
        await queue_manager.add_job(
            chat_id=chat_id,
            user_id=user_id,
            handler_func=func,
            update=update,
            context=context
        )
        
        # Trả về OK ngay lập tức (Telegram sẽ nhận được response nhanh)
        return
        
    return wrapper

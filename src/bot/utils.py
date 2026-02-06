from datetime import datetime, timedelta
from telegram import Update
from src.bot.constants import TICKET_DISPLAY_NAMES, stats, last_results
from src.db.sqlite_store import load_stats, load_last_result
from src.bot.session_manager import SessionManager

session_manager = SessionManager()

def ticket_display_name(code: str) -> str:
    """Trả về tên hiển thị của vé, hoặc mã gốc nếu không có map."""
    return TICKET_DISPLAY_NAMES.get(code, code)

def escape_markdown(text: str) -> str:
    """Escape các ký tự đặc biệt trong Markdown"""
    special_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def get_chat_stats(chat_id: int) -> dict:
    """
    Lấy thống kê cho một chat.
    Ưu tiên cache RAM, nếu chưa có thì load từ SQLite.
    """
    chat_stats = stats.get(chat_id)
    if chat_stats is not None:
        return chat_stats

    loaded = load_stats(chat_id)
    if loaded:
        stats[chat_id] = loaded
        return loaded

    # Nếu chưa có trong DB thì khởi tạo rỗng
    empty = {"wins": {}, "participations": {}}
    stats[chat_id] = empty
    return empty

def get_last_result_for_chat(chat_id: int) -> dict | None:
    """
    Lấy kết quả game gần nhất cho một chat.
    Ưu tiên cache RAM, nếu chưa có thì load từ SQLite.
    """
    data = last_results.get(chat_id)
    if data is not None:
        return data

    loaded = load_last_result(chat_id)
    if loaded:
        last_results[chat_id] = loaded
        return loaded
    return None

def is_session_expired(session) -> bool:
    """Kiểm tra session có hết hạn do lâu không hoạt động (không quay số) hay không."""
    if not hasattr(session, "last_activity"):
        return False
    
    # 2 giờ không có hoạt động thì coi như hết hạn
    expiry_limit = timedelta(hours=2)
    return datetime.now() - session.last_activity > expiry_limit

async def ensure_active_session(update: Update, chat_id: int, session) -> bool:
    """
    Đảm bảo session còn hiệu lực.
    Nếu đã hết hạn: xoá session, thông báo cho user và trả về False.
    """
    if is_session_expired(session):
        session_manager.delete_session(chat_id)
        # Handle cases where update.message might be None (e.g. CallbackQuery)
        msg_target = update.message if update.message else update.callback_query.message
        await msg_target.reply_text(
            "⏱️ *Game đã hết hạn do quá lâu không quay số\\!* \n\n"
            "Host hãy dùng `/moi <tên_game>` hoặc `/pham_vi <x> <y>` để tạo game mới nhé.",
            parse_mode="Markdown",
        )
        return False
    return True

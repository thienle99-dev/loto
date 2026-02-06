""" 
Telegram bot handlers và commands 
""" 
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton 
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
import sys
from pathlib import Path

# Thêm thư mục gốc vào PYTHONPATH nếu chưa có
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.bot.wheel import (
    spin_wheel,
    reset_session,
    set_remove_mode,
    get_session_status
)
from src.bot.session_manager import SessionManager
from src.utils.validators import validate_range, validate_number
from config.config import (
    WELCOME_MESSAGE,
    HELP_MESSAGE,
    MAX_NUMBERS,
    DEFAULT_REMOVE_AFTER_SPIN
)
from src.db.sqlite_store import (
    load_stats,
    save_stats,
    load_last_result,
    save_last_result,
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Session manager (shared instance)
session_manager = SessionManager()

# Lưu kết quả game gần nhất theo chat (cache RAM): {chat_id: {...}}
last_results: dict[int, dict] = {}

# Thống kê wins/participations theo chat (cache RAM)
stats: dict[int, dict] = {}

# Vòng chơi (vòng mới) đang hoạt động theo chat:
# {chat_id: {"round_name": str, "owner_id": int, "created_at": str}}
active_rounds: dict[int, dict] = {}

# Cooldown chống spam
COOLDOWN_SPIN_SECONDS = 2
COOLDOWN_CHECK_SECONDS = 2
last_spin_time: dict[int, datetime] = {}
last_check_time: dict[tuple[int, int], datetime] = {}

# Timeout session nếu quá lâu không quay (tính theo phút)
SESSION_TIMEOUT_MINUTES = 10

# Danh sách mã vé/màu cho game
TICKET_CODES: list[str] = [
    "cam1",
    "cam2",
    "do1",
    "do2",
    "duong1",
    "duong2",
    "hong1",
    "hong2",
    "luc1",
    "luc2",
    "tim1",
    "tim2",
    "vang1",
    "vang2",
    "xanh1",
    "xanh2",
]

# Map mã vé -> đường dẫn ảnh tương ứng (chỉ gửi ảnh nếu file tồn tại)
TICKET_IMAGES: dict[str, Path] = {
    "cam1": Path(__file__).parent.parent.parent / "images" / "cam_1.jpg",
    "cam2": Path(__file__).parent.parent.parent / "images" / "cam_2.jpg",
    "do1": Path(__file__).parent.parent.parent / "images" / "do_1.jpg",
    "do2": Path(__file__).parent.parent.parent / "images" / "do_2.jpg",
    "duong1": Path(__file__).parent.parent.parent / "images" / "duong_1.jpg",
    "duong2": Path(__file__).parent.parent.parent / "images" / "duong_2.jpg",
    "hong1": Path(__file__).parent.parent.parent / "images" / "hong_1.jpg",
    "hong2": Path(__file__).parent.parent.parent / "images" / "hong_2.jpg",
    "luc1": Path(__file__).parent.parent.parent / "images" / "luc_1.jpg",
    "luc2": Path(__file__).parent.parent.parent / "images" / "luc_2.jpg",
    "tim1": Path(__file__).parent.parent.parent / "images" / "tim_1.jpg",
    "tim2": Path(__file__).parent.parent.parent / "images" / "tim_2.jpg",
    "vang1": Path(__file__).parent.parent.parent / "images" / "vang_1.jpg",
    "vang2": Path(__file__).parent.parent.parent / "images" / "vang_2.jpg",
    "xanh1": Path(__file__).parent.parent.parent / "images" / "xanh_1.jpg",
    "xanh2": Path(__file__).parent.parent.parent / "images" / "xanh_2.jpg",
}


def escape_markdown(text: str) -> str:
    """Escape các ký tự đặc biệt trong Markdown"""
    # Escape các ký tự đặc biệt của Markdown
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


async def vongmoi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /vong_moi <tên_vòng> - tạo vòng chơi mới trong chat."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id

    if not context.args:
        await update.message.reply_text(
            "❌ *Sai cú pháp\\!*\n\n"
            "Sử dụng: `/vong_moi <tên_vòng>`\n"
            "Ví dụ: `/vong_moi Loto tối nay`",
            parse_mode="Markdown",
        )
        return

    round_name = " ".join(context.args).strip()
    if not round_name:
        await update.message.reply_text(
            "❌ Tên vòng không được để trống.",
            parse_mode="Markdown",
        )
        return

    # Kiểm tra nếu đã có vòng đang hoạt động
    if chat_id in active_rounds:
        current_round = active_rounds[chat_id].get("round_name", "Không tên")
        await update.message.reply_text(
            f"⚠️ *Đang có vòng chơi hoạt động\\!*\n\n"
            f"Vòng: `{escape_markdown(current_round)}`\n"
            f"Vui lòng dùng `/ket_thuc_vong` để kết thúc vòng cũ trước khi tạo vòng mới\\.",
            parse_mode="Markdown",
        )
        return

    # Nếu đang có vòng cũ, ghi đè bằng vòng mới
    active_rounds[chat_id] = {
        "round_name": round_name,
        "owner_id": user_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    await update.message.reply_text(
        f"✅ *Đã tạo vòng chơi mới\\!* \n\n"
        f"🔄 Tên vòng: `{escape_markdown(round_name)}`\n\n"
        "Giờ bạn có thể dùng:\n"
        "• `/moi <tên_game>` hoặc `/pham_vi <x> <y>` để tạo các game trong vòng này.\n"
        "• `/ket_thuc` để kết thúc từng game.\n"
        "• `/ket_thuc_vong` để kết thúc vòng chơi.",
        parse_mode="Markdown",
    )


async def endround_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /ket_thuc_vong - kết thúc vòng chơi hiện tại"""
    chat_id = update.effective_chat.id
    
    if chat_id not in active_rounds:
         await update.message.reply_text(
            "ℹ️ Hiện không có vòng chơi nào đang hoạt động.",
            parse_mode='Markdown'
        )
         return

    round_info = active_rounds[chat_id]
    round_name = round_info.get("round_name", "Không tên")
    
    # Xoá vòng chơi khỏi active_rounds
    del active_rounds[chat_id]
    
    await update.message.reply_text(
        f"🛑 Đã kết thúc vòng chơi *{escape_markdown(round_name)}*\\.\n\n"
        "Giờ bạn có thể tạo vòng mới bằng `/vong_moi <tên_vòng>`\\.",
        parse_mode='Markdown'
    )


def is_session_expired(session) -> bool:
    """Kiểm tra session có hết hạn do lâu không hoạt động (không quay số) hay không."""
    timeout = timedelta(minutes=SESSION_TIMEOUT_MINUTES)

    # Nếu đã có lịch sử quay, dùng thời gian lần quay gần nhất
    if getattr(session, "history", None):
        last_time_str = session.history[-1].get("time")
        try:
            last_time = datetime.fromisoformat(last_time_str)
        except Exception:
            last_time = session.updated_at
    else:
        # Chưa quay lần nào: dùng thời gian tạo game
        last_time = getattr(session, "updated_at", getattr(session, "created_at", datetime.now()))

    return datetime.now() - last_time > timeout


async def ensure_active_session(update: Update, chat_id: int, session) -> bool:
    """
    Đảm bảo session còn hiệu lực.
    Nếu đã hết hạn: xoá session, thông báo cho user và trả về False.
    """
    if is_session_expired(session):
        session_manager.delete_session(chat_id)
        await update.message.reply_text(
            "⏱️ *Game đã hết hạn do quá lâu không quay số\\!* \n\n"
            "Host hãy dùng `/moi <tên_game>` hoặc `/pham_vi <x> <y>` để tạo game mới nhé.",
            parse_mode="Markdown",
        )
        return False
    return True


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /start - hiển thị hướng dẫn tổng quan"""
    await update.message.reply_text(
        WELCOME_MESSAGE,
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /help"""
    await update.message.reply_text(
        HELP_MESSAGE,
        parse_mode='Markdown'
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /menu - hiển thị menu phím bấm nhanh"""
    keyboard = [
        [
            KeyboardButton("/moi"),
            KeyboardButton("/tham_gia"),
            KeyboardButton("/danh_sach"),
        ],
        [
            KeyboardButton("/quay"),
            KeyboardButton("/kinh"),
            KeyboardButton("/trang_thai"),
        ],
        [
            KeyboardButton("/lich_su"),
            KeyboardButton("/dat_lai"),
        ],
        [
            KeyboardButton("/ket_thuc"),
            KeyboardButton("/tra_ve"),
            KeyboardButton("/xoa"),
        ],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )

    text = (
        "📋 *Menu thao tác nhanh*\n\n"
        "🕹️ *Vòng chơi & game*\n"
        "• `/vong_moi <tên_vòng>` \\- tạo vòng chơi mới trong chat\n"
        "• `/moi <tên_game>` \\- tạo game mới trong vòng / chat\n"
        "• `/pham_vi <x> <y>` \\- tạo game với khoảng số tuỳ chỉnh\n"
        "• `/bat_dau` \\- host bấm để *bắt đầu* game\n"
        "• `/tham_gia` \\- tham gia game hiện tại\n"
        "• `/danh_sach` \\- xem danh sách người chơi\n"
        "• `/tra_ve` \\- rời khỏi game (người thường)\n\n"
        "🎲 *Quay số & trạng thái*\n"
        "• `/quay` \\- quay số\n"
        "• `/kinh <dãy_số>` \\- kiểm tra vé, số đã/ chưa quay\n"
        "• `/trang_thai` \\- xem trạng thái hiện tại\n"
        "• `/lich_su` \\- lịch sử quay gần đây\n\n"
        "⚙️ *Quản lý phiên chơi*\n"
        "• `/dat_lai` \\- reset lại dãy số\n"
        "• `/ket_thuc` \\- kết thúc game (chỉ host)\n"
        "• `/xoa` \\- xoá session trong chat\n\n"
        "📊 *Thống kê & kết quả*\n"
        "• `/ket_qua` \\- xem kết quả game gần nhất trong chat\n"
        "• `/xep_hang` \\- bảng xếp hạng trúng thưởng (mặc định)\n"
        "ℹ️ *Khác*\n"
        "• `/tro_giup` \\- hướng dẫn chi tiết\n\n"
        "_Chọn nhanh nút bên dưới rồi bổ sung tham số nếu cần, ví dụ:_\n"
        "• `/moi Loto tối nay`\n"
        "• `/kinh 1 5 10 20`"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def newsession_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /moi <tên_game>
    
    Tạo một session mới với tên game, sử dụng khoảng số mặc định 1 -> MAX_NUMBERS.
    """
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id

    # Không cho tạo session mới nếu chat đang có session chưa end
    if session_manager.has_session(chat_id):
        await update.message.reply_text(
            "⚠️ Chat này đang có game hoạt động\\. "
            "Vui lòng dùng `/ket_thuc` để kết thúc hoặc `/xoa` để xoá trước khi tạo game mới\\.",
            parse_mode='Markdown'
        )
        return

    if not context.args:
        await update.message.reply_text(
            "❌ *Sai cú pháp\\!*\n\n"
            "Sử dụng: `/moi <tên_game>`\n"
            "Ví dụ: `/moi Loto tối nay`",
            parse_mode='Markdown'
        )
        return

    game_name = " ".join(context.args).strip()

    if not game_name:
        await update.message.reply_text(
            "❌ Tên game không được để trống.",
            parse_mode='Markdown'
        )
        return

    try:
        # Tạo session với khoảng mặc định 1 -> MAX_NUMBERS (theo từng chat)
        session = session_manager.create_session(
            chat_id,
            1,
            MAX_NUMBERS,
            DEFAULT_REMOVE_AFTER_SPIN
        )
        # Gắn thêm meta vào session
        session.game_name = game_name
        session.owner_id = user_id

        # Nếu đang có vòng chơi active thì gắn tên vòng vào session
        round_info = active_rounds.get(chat_id)
        if round_info:
            session.round_name = round_info.get("round_name")

        # Owner auto join
        session.add_participant(user_id=user_id, name=user.full_name or (user.username or str(user_id)))

        # Lưu session xuống DB
        session_manager.persist_session(chat_id)

        await update.message.reply_text(
            f"✅ *Đã tạo game mới\\!*\n\n"
            f"🕹️ Tên game: `{escape_markdown(game_name)}`\n"
            f"📊 Khoảng số: `1 -> {MAX_NUMBERS}`\n"
            f"📊 Tổng số: `{session.get_total_numbers()}`\n"
            f"⚙️ Loại bỏ sau khi quay: `{'Có' if session.remove_after_spin else 'Không'}`\n\n"
            "Người chơi dùng `/lay_ve ma_ve` để chọn vé và `/tra_ve` để rời game.\n"
            "Host gửi `/bat_dau` để bắt đầu game, sau đó dùng `/quay` để quay và `/kinh danh_sach_so` để kiểm tra vé.",
            parse_mode='Markdown'
        )
    except ValueError as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")


async def setrange_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /pham_vi <x> <y>"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    
    # Không cho tạo session mới nếu chat đang có session chưa end
    if session_manager.has_session(chat_id):
        await update.message.reply_text(
            "⚠️ Chat này đang có game hoạt động\\. "
            "Vui lòng dùng `/ket_thuc` để kết thúc hoặc `/xoa` để xoá trước khi tạo game mới\\.",
            parse_mode='Markdown'
        )
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ *Sai cú pháp\\!*\n\n"
            "Sử dụng: `/pham_vi <x> <y>`\n"
            "Ví dụ: `/pham_vi 1 100`",
            parse_mode='Markdown'
        )
        return
    
    # Parse arguments
    start_arg = context.args[0]
    end_arg = context.args[1]
    
    # Validate numbers
    is_valid_start, start_num, error_start = validate_number(start_arg)
    is_valid_end, end_num, error_end = validate_number(end_arg)
    
    if not is_valid_start:
        await update.message.reply_text(f"❌ Lỗi: {error_start}")
        return
    
    if not is_valid_end:
        await update.message.reply_text(f"❌ Lỗi: {error_end}")
        return
    
    # Validate range
    is_valid, error_msg = validate_range(start_num, end_num)
    if not is_valid:
        await update.message.reply_text(f"❌ Lỗi: {error_msg}")
        return
    
    try:
        # Create session theo từng chat
        session = session_manager.create_session(
            chat_id,
            start_num,
            end_num,
            DEFAULT_REMOVE_AFTER_SPIN
        )
        session.owner_id = user_id

        # Nếu đang có vòng chơi active thì gắn tên vòng vào session
        round_info = active_rounds.get(chat_id)
        if round_info:
            session.round_name = round_info.get("round_name")

        session.add_participant(user_id=user_id, name=user.full_name or (user.username or str(user_id)))

        # Lưu session xuống DB
        session_manager.persist_session(chat_id)
        
        await update.message.reply_text(
            f"✅ *Đã tạo game mới\\!*\n\n"
            f"📊 Khoảng số: `{start_num} -> {end_num}`\n"
            f"📊 Tổng số: `{session.get_total_numbers()}`\n"
            f"⚙️ Loại bỏ sau khi quay: `{'Có' if session.remove_after_spin else 'Không'}`\n\n"
            f"Host gửi `/bat_dau` để bắt đầu game, sau đó dùng `/quay` để quay và `/kinh <danh_sách_số>` để kiểm tra vé\\.",
            parse_mode='Markdown'
        )
    except ValueError as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")


async def spin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /quay"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)
    
    # Cooldown theo chat để tránh spam quay
    now = datetime.now()
    last_time = last_spin_time.get(chat_id)
    if last_time and (now - last_time).total_seconds() < COOLDOWN_SPIN_SECONDS:
        wait = COOLDOWN_SPIN_SECONDS - (now - last_time).total_seconds()
        await update.message.reply_text(
            f"⏱️ Vui lòng đợi khoảng `{wait:.1f}` giây nữa rồi mới quay tiếp.",
            parse_mode='Markdown'
        )
        return

    if not session:
        await update.message.reply_text(
            "❌ *Chưa có game nào trong chat\\!*\n\n"
            "Host dùng `/moi <tên_game>` hoặc `/pham_vi <x> <y>` để tạo game trước nhé\\.",
            parse_mode='Markdown'
        )
        return

    # Kiểm tra timeout session
    if not await ensure_active_session(update, chat_id, session):
        return

    # Yêu cầu host đã /bat_dau trước khi quay
    if not getattr(session, "started", False):
        await update.message.reply_text(
            "⏱️ *Game chưa bắt đầu\\!* \n\n"
            "Host cần dùng lệnh `/bat_dau` để bắt đầu game trước khi quay số.",
            parse_mode='Markdown'
        )
        return
    
    try:
        # Spin wheel
        number = spin_wheel(session)
        last_spin_time[chat_id] = now
        
        # Format message
        message = f"🎲 *Số được chọn: `{number}`*\n\n"
        message += f"📊 Còn lại: `{session.get_remaining_count()}/{session.get_total_numbers()}`"
        
        if session.is_empty():
            message += "\n\n⚠️ Danh sách đã hết\\! Sử dụng `/reset` để làm mới\\."
        
        await update.message.reply_text(message, parse_mode='Markdown')

        # Lưu session sau khi quay
        session_manager.persist_session(chat_id)
    except ValueError as e:
        await update.message.reply_text(f"❌ {str(e)}")


async def toggle_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /toggle_remove - tạm thời vẫn dùng tên kỹ thuật để admin cấu hình"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)
    
    if not session:
        await update.message.reply_text(
            "❌ *Chưa có game nào trong chat\\!*\n\n"
            "Host dùng `/moi <tên_game>` hoặc `/pham_vi <x> <y>` để tạo game trước nhé\\.",
            parse_mode='Markdown'
        )
        return
    
    # Toggle remove mode
    new_mode = not session.remove_after_spin
    set_remove_mode(session, new_mode)
    
    # Lưu cấu hình session
    session_manager.persist_session(chat_id)

    mode_text = "Có" if new_mode else "Không"
    await update.message.reply_text(
        f"⚙️ *Chế độ loại bỏ:* `{mode_text}`\n\n"
        f"{'✅ Số đã quay sẽ bị loại bỏ' if new_mode else '✅ Số đã quay vẫn có thể xuất hiện lại'}",
        parse_mode='Markdown'
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /dat_lai"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)
    
    if not session:
        await update.message.reply_text(
            "❌ *Chưa có game nào trong chat\\!*\n\n"
            "Host dùng `/moi <tên_game>` hoặc `/pham_vi <x> <y>` để tạo game trước nhé\\.",
            parse_mode='Markdown'
        )
        return
    
    reset_session(session)
    # Lưu session sau khi reset
    session_manager.persist_session(chat_id)

    await update.message.reply_text(
        f"🔄 *Đã reset\\!*\n\n"
        f"📊 Danh sách đã được khôi phục về ban đầu\\.\n"
        f"📊 Số còn lại: `{session.get_remaining_count()}/{session.get_total_numbers()}`",
        parse_mode='Markdown'
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /trang_thai"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)
    
    if not session:
        await update.message.reply_text(
            "❌ *Chưa có game nào trong chat\\!*\n\n"
            "Host dùng `/moi <tên_game>` hoặc `/pham_vi <x> <y>` để tạo game trước nhé\\.",
            parse_mode='Markdown'
        )
        return

    # Kiểm tra timeout session
    if not await ensure_active_session(update, chat_id, session):
        return
    
    status = get_session_status(session)
    
    message = "📋 *Trạng thái session:*\n\n"
    message += f"📊 Khoảng số: `{status['range']}`\n"
    message += f"📊 Tổng số: `{status['total_numbers']}`\n"
    message += f"📊 Còn lại: `{status['remaining_count']}`\n"
    message += f"📊 Đã loại bỏ: `{status['removed_count']}`\n"
    message += f"⚙️ Loại bỏ sau khi quay: `{'Có' if status['remove_after_spin'] else 'Không'}`\n"
    message += f"🎲 Số lần quay: `{status['spin_count']}`\n"
    
    if status['last_spin'] is not None:
        message += f"🎯 Số vừa quay: `{status['last_spin']}`\n"
    
    if status['is_empty']:
        message += "\n⚠️ Danh sách đã hết\\!"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /lich_su - hiển thị toàn bộ lịch sử quay của game hiện tại"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)
    
    if not session:
        await update.message.reply_text(
            "❌ *Chưa có game nào trong chat\\!*\n\n"
            "Host dùng `/moi <tên_game>` hoặc `/pham_vi <x> <y>` để tạo game trước nhé\\.",
            parse_mode='Markdown'
        )
        return

    # Kiểm tra timeout session
    if not await ensure_active_session(update, chat_id, session):
        return
    
    # Lấy toàn bộ lịch sử quay từ đầu đến giờ
    history = session.history
    if not history:
        await update.message.reply_text(
            "ℹ️ Chưa có lịch sử quay nào.",
            parse_mode='Markdown'
        )
        return
    
    lines = []
    # Hiển thị theo thứ tự thời gian (từ lần quay đầu tiên)
    for idx, item in enumerate(history, start=1):
        number = item.get("number")
        time_str = item.get("time")
        lines.append(f"{idx}. `{number}` (lúc {time_str})")
    
    message = "📜 *Lịch sử quay của game hiện tại:*\n\n" + "\n".join(lines)
    await update.message.reply_text(message, parse_mode='Markdown')


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /xoa"""
    chat_id = update.effective_chat.id
    
    if not session_manager.has_session(chat_id):
        await update.message.reply_text(
            "ℹ️ Không có session để xóa.",
            parse_mode='Markdown'
        )
        return
    
    session_manager.delete_session(chat_id)
    
    await update.message.reply_text(
        "🗑️ *Đã xóa session\\!*\n\n"
        "Host có thể dùng `/moi <tên_game>` hoặc `/pham_vi <x> <y>` để tạo game mới\\.",
        parse_mode='Markdown'
    )


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /tham_gia - cho phép người khác tham gia game hiện tại trong nhóm/chat"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    session = session_manager.get_session(chat_id)

    if not session:
        await update.message.reply_text(
            "❌ *Chưa có game nào đang chạy trong chat này\\!*\n\n"
            "Host dùng `/moi <tên_game>` để tạo game mới.",
            parse_mode='Markdown'
        )
        return

    display_name = user.full_name or (user.username or str(user_id))
    is_new = session.add_participant(user_id=user_id, name=display_name)

    game_name = getattr(session, "game_name", None)
    if is_new:
        text = f"✅ *{escape_markdown(display_name)}* đã tham gia game hiện tại."
    else:
        text = f"ℹ️ *{escape_markdown(display_name)}* đã ở trong danh sách người chơi."

    if game_name:
        text = f"{text}\n\n🕹️ Game: `{escape_markdown(game_name)}`"

    await update.message.reply_text(text, parse_mode='Markdown')


async def out_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /tra_ve - cho phép người chơi rời khỏi game"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    session = session_manager.get_session(chat_id)

    if not session:
        await update.message.reply_text(
            "❌ Không có game nào đang chạy trong chat này.",
            parse_mode='Markdown'
        )
        return

    # Nếu game đã start thì không cho phép out nữa
    if getattr(session, "started", False):
        await update.message.reply_text(
            "⏱️ Game đã bắt đầu, không thể dùng `/tra_ve` để rời game nữa.",
            parse_mode='Markdown'
        )
        return

    # Host không được out, phải dùng /ket_thuc
    if getattr(session, "owner_id", None) == user_id:
        await update.message.reply_text(
            "❌ Bạn là chủ phòng\\. Dùng `/ket_thuc` để kết thúc game thay vì `/tra_ve`.",
            parse_mode='Markdown'
        )
        return

    removed = session.remove_participant(user_id)
    if removed:
        await update.message.reply_text(
            "✅ Bạn đã rời khỏi game hiện tại.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "ℹ️ Bạn không nằm trong danh sách người chơi của game hiện tại.",
            parse_mode='Markdown'
        )


async def players_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /danh_sach - hiển thị danh sách người tham gia game"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)

    if not session:
        await update.message.reply_text(
            "❌ *Chưa có game nào đang chạy trong chat này\\!*",
            parse_mode='Markdown'
        )
        return

    participants = session.get_participants()
    owner_id = getattr(session, "owner_id", None)
    game_name = getattr(session, "game_name", None)

    if not participants and owner_id is None:
        await update.message.reply_text(
            "ℹ️ Hiện chưa có ai tham gia game.",
            parse_mode='Markdown'
        )
        return

    # Sắp xếp: chủ phòng lên đầu
    lines = []
    count = 0

    # Gom theo owner_id nếu có
    owner_line_done = False
    for p in participants:
        uid = p.get("user_id")
        name = p.get("name") or str(uid)
        prefix = "-"
        suffix = ""
        if owner_id is not None and uid == owner_id and not owner_line_done:
            prefix = "⭐"
            suffix = " *(Host)*"
            owner_line_done = True
        lines.append(f"{prefix} {escape_markdown(name)}{suffix}")
        count += 1

    # Nếu chưa thấy owner trong participants nhưng có owner_id thì thêm
    if owner_id is not None and not owner_line_done:
        lines.insert(0, "⭐ Chủ phòng (Host)")
        count += 1

    header = "👥 *Danh sách người tham gia game:*\n\n"
    if game_name:
        header += f"🕹️ Game: `{escape_markdown(game_name)}`\n"
    header += f"📊 Tổng: `{count}` người\n\n"

    await update.message.reply_text(
        header + "\n".join(lines),
        parse_mode='Markdown'
    )

    # Chỉ hiển thị, không thay đổi session -> không cần lưu


async def startsession_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /bat_dau - host bấm để bắt đầu game"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    session = session_manager.get_session(chat_id)

    if not session:
        await update.message.reply_text(
            "❌ *Chưa có game nào để bắt đầu\\!* \n\n"
            "Host dùng `/moi <tên_game>` hoặc `/pham_vi <x> <y>` để tạo game trước.",
            parse_mode='Markdown'
        )
        return

    owner_id = getattr(session, "owner_id", None)
    if owner_id is not None and owner_id != user_id:
        await update.message.reply_text(
            "❌ Chỉ *host* (người tạo game) mới được quyền bắt đầu game bằng `/bat_dau`.",
            parse_mode='Markdown'
        )
        return

    if getattr(session, "started", False):
        await update.message.reply_text(
            "ℹ️ Game này đã được bắt đầu trước đó rồi.",
            parse_mode='Markdown'
        )
        return

    session.started = True

    # Lưu trạng thái bắt đầu game
    session_manager.persist_session(chat_id)

    game_name = getattr(session, "game_name", None)
    if game_name:
        text = (
            f"🚀 *Game đã bắt đầu\\!* \n\n"
            f"🕹️ `{escape_markdown(game_name)}`\n\n"
            "Mọi người có thể dùng:\n"
            "• `/quay` để quay số\n"
            "• `/kinh <dãy_số>` để kiểm tra vé"
        )
    else:
        text = (
            "🚀 *Game đã bắt đầu\\!* \n\n"
            "Mọi người có thể dùng:\n"
            "• `/quay` để quay số\n"
            "• `/kinh <dãy_số>` để kiểm tra vé"
        )

    await update.message.reply_text(text, parse_mode='Markdown')


async def lastresult_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /ket_qua - hiển thị kết quả game gần nhất trong chat"""
    chat_id = update.effective_chat.id
    data = get_last_result_for_chat(chat_id)

    if not data:
        await update.message.reply_text(
            "ℹ️ Chưa có game nào kết thúc trong chat này, hoặc bot chưa lưu kết quả.",
            parse_mode='Markdown'
        )
        return

    game_name = data.get("game_name") or "Không đặt tên"
    host_name = data.get("host_name") or "Host"
    ended_at = data.get("ended_at") or ""
    numbers_drawn = data.get("numbers_drawn") or []
    winners = data.get("winners") or []

    # Lấy danh sách số đã quay (giới hạn hiển thị)
    drawn_list = [item.get("number") for item in numbers_drawn if item.get("number") is not None]
    total_spins = len(drawn_list)
    if drawn_list:
        # Hiển thị tối đa 20 số cuối cùng
        shown = drawn_list[-20:]
        numbers_str = ", ".join(f"`{n}`" for n in shown)
        if total_spins > 20:
            numbers_str = f"... , {numbers_str}"
    else:
        numbers_str = "_Chưa quay số nào_"

    msg = (
        "📊 *Kết quả game gần nhất trong chat:*\n\n"
        f"🕹️ Tên game: `{escape_markdown(str(game_name))}`\n"
        f"⭐ Host: `{escape_markdown(str(host_name))}`\n"
        f"⏱️ Kết thúc lúc: `{escape_markdown(str(ended_at))}`\n"
        f"🎲 Tổng lượt quay: `{total_spins}`\n"
        f"🎯 Một số lần quay gần nhất: {numbers_str}\n\n"
    )

    if winners:
        msg += "🏆 *Người trúng thưởng:*\n"
        for w in winners:
            w_name = escape_markdown(str(w.get("name") or w.get("user_id")))
            nums = w.get("numbers") or []
            nums_str = ", ".join(f"`{n}`" for n in nums)
            msg += f"- {w_name}: {nums_str}\n"
    else:
        msg += "🏆 *Không có ai trúng thưởng trong game này\\.*\n"

    await update.message.reply_text(msg, parse_mode='Markdown')


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /xep_hang - bảng xếp hạng trúng thưởng / tham gia"""
    chat_id = update.effective_chat.id
    chat_stats = get_chat_stats(chat_id)

    if not chat_stats:
        await update.message.reply_text(
            "ℹ️ Chưa có dữ liệu thống kê trong chat này.",
            parse_mode='Markdown'
        )
        return

    mode = "wins"
    if context.args:
        arg = context.args[0].lower()
        if arg.startswith("join") or arg.startswith("part"):
            mode = "participations"

    wins = chat_stats.get("wins", {})
    participations = chat_stats.get("participations", {})

    if mode == "wins":
        if not wins:
            await update.message.reply_text(
                "ℹ️ Chưa có ai trúng thưởng trong chat này.",
                parse_mode='Markdown'
            )
            return
        sorted_items = sorted(
            wins.items(),
            key=lambda kv: kv[1].get("count", 0.0),
            reverse=True
        )[:10]
        title = "🏆 *Top người trúng thưởng nhiều nhất:*"
    else:
        if not participations:
            await update.message.reply_text(
                "ℹ️ Chưa có ai tham gia game trong chat này.",
                parse_mode='Markdown'
            )
            return
        sorted_items = sorted(
            participations.items(),
            key=lambda kv: kv[1].get("count", 0.0),
            reverse=True
        )[:10]
        title = "👥 *Top người tham gia nhiều game nhất:*"

    lines = []
    for idx, (uid, info) in enumerate(sorted_items, start=1):
        name = escape_markdown(str(info.get("name") or uid))
        count = float(info.get("count", 0.0))
        # Hiển thị số nguyên nếu tròn, ngược lại hiển thị 2 chữ số thập phân
        if count.is_integer():
            count_str = str(int(count))
        else:
            count_str = f"{count:.2f}"
        lines.append(f"{idx}. {name} - `{count_str}` lần")

    mode_hint = (
        "\n\nℹ️ Dùng `/xep_hang wins` hoặc `/xep_hang join` để xem bảng xếp hạng tương ứng."
    )

    await update.message.reply_text(
        f"{title}\n\n" + "\n".join(lines) + mode_hint,
        parse_mode='Markdown'
    )


async def endsession_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /ket_thuc
    
    Chỉ người đã tạo session (/moi hoặc /pham_vi) mới được phép kết thúc.
    """
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    session = session_manager.get_session(chat_id)

    if not session:
        await update.message.reply_text(
            "ℹ️ Hiện không có game nào đang chạy để kết thúc.",
            parse_mode='Markdown'
        )
        return

    # Nếu có gắn owner_id thì kiểm tra, mặc dù hiện tại session được map theo user_id
    owner_id = getattr(session, "owner_id", user_id)
    if owner_id != user_id:
        await update.message.reply_text(
            "❌ Chỉ *host* (người tạo game) mới được quyền kết thúc game với `/ket_thuc`.",
            parse_mode='Markdown'
        )
        return

    game_name = getattr(session, "game_name", None)

    # Cập nhật thống kê cho leaderboard (trong cache & DB)
    chat_stats = get_chat_stats(chat_id)

    # 1) Số lần tham gia dựa trên participants
    participations = chat_stats["participations"]
    for p in session.get_participants():
        uid = p.get("user_id")
        if uid is None:
            continue
        name = p.get("name") or str(uid)
        info = participations.get(uid, {"count": 0.0, "name": name})
        info["count"] += 1.0
        info["name"] = name
        participations[uid] = info

    # 2) Số lần trúng thưởng: chia đều 1 điểm cho tất cả người trúng trong game này
    wins = chat_stats["wins"]
    winners_list = list(getattr(session, "winners", []))
    unique_winners: dict[int, str] = {}
    for w in winners_list:
        uid = w.get("user_id")
        if uid is None:
            continue
        name = w.get("name") or str(uid)
        unique_winners[uid] = name

    total_winners = len(unique_winners)
    if total_winners > 0:
        share = 1.0 / total_winners
        for uid, name in unique_winners.items():
            info = wins.get(uid, {"count": 0.0, "name": name})
            info["count"] += share
            info["name"] = name
            wins[uid] = info

    # Lưu kết quả game gần nhất cho chat này
    host_name = user.full_name or (user.username or str(user_id))
    result_data = {
        "game_name": game_name,
        "host_id": user_id,
        "host_name": host_name,
        "numbers_drawn": list(session.history),
        "winners": list(getattr(session, "winners", [])),
        "ended_at": datetime.now().isoformat(timespec="seconds"),
    }
    last_results[chat_id] = result_data

    # Lưu stats + last_result xuống DB
    save_stats(chat_id, chat_stats)
    save_last_result(chat_id, result_data)

    session_manager.delete_session(chat_id)

    if game_name:
        msg = (
            f"🛑 *Đã kết thúc ván chơi* `{escape_markdown(game_name)}`\\.\n\n"
            "Bạn có thể tạo ván chơi mới bằng `/moi <tên_game>`"

        )
    else:
        msg = (
            "🛑 *Đã kết thúc vòng chơi hiện tại\\!* \n\n"
            "Bạn có thể tạo vòng mới bằng `/vong_moi <tên_vòng>`."
        )

    await update.message.reply_text(msg, parse_mode='Markdown')


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /kinh <danh_sách_số>
    
    Ví dụ: /kinh 1 2 3 10 20
            /kinh 1,5,10,15
    Bot sẽ báo số nào đã quay, số nào chưa quay hoặc không hợp lệ.
    """
    chat_id = update.effective_chat.id
    user = update.effective_user
    session = session_manager.get_session(chat_id)

    # Cooldown theo user trong từng chat để tránh spam check
    key = (chat_id, user.id)
    now = datetime.now()
    last_time = last_check_time.get(key)
    if last_time and (now - last_time).total_seconds() < COOLDOWN_CHECK_SECONDS:
        await update.message.reply_text(
            "⏱️ Bạn vừa /kinh xong, đợi vài giây rồi thử lại nhé.",
            parse_mode='Markdown'
        )
        return

    if not session:
        await update.message.reply_text(
            "❌ *Chưa có game nào trong chat\\!*\n\n"
            "Host dùng `/moi <tên_game>` hoặc `/pham_vi <x> <y>` để tạo game trước nhé\\.",
            parse_mode='Markdown'
        )
        return

    # Kiểm tra timeout session
    if not await ensure_active_session(update, chat_id, session):
        return

    # Yêu cầu game đã được host /bat_dau
    if not getattr(session, "started", False):
        await update.message.reply_text(
            "⏱️ *Game chưa bắt đầu\\!* \n\n"
            "Host cần dùng lệnh `/bat_dau` để bắt đầu game trước khi kiểm tra vé.",
            parse_mode='Markdown'
        )
        return

    if not context.args:
        await update.message.reply_text(
            "❌ *Sai cú pháp\\!*\n\n"
            "Sử dụng: `/kinh <danh_sách_số>`\n"
            "Ví dụ: `/kinh 1 5 10 20 30` hoặc `/kinh 1,5,10,20,30`",
            parse_mode='Markdown'
        )
        return

    raw_text = " ".join(context.args)
    # Chấp nhận cả dấu phẩy và khoảng trắng
    for ch in [",", ";", "|"]:
        raw_text = raw_text.replace(ch, " ")

    tokens = [t for t in raw_text.split() if t.strip()]
    if not tokens:
        await update.message.reply_text(
            "❌ Không tìm thấy số nào để kiểm tra.",
            parse_mode='Markdown'
        )
        return

    drawn_numbers = {item.get("number") for item in session.history}
    remaining_numbers = set(session.available_numbers)

    matched = []
    not_drawn = []
    invalid = []

    for token in tokens:
        is_valid, number, error = validate_number(token)
        if not is_valid:
            invalid.append(token)
            continue

        # Kiểm tra trong khoảng session
        if number < session.start_number or number > session.end_number:
            invalid.append(str(number))
            continue

        if number in drawn_numbers:
            matched.append(number)
        elif number in remaining_numbers:
            not_drawn.append(number)
        else:
            # Không còn trong available_numbers và cũng chưa thấy trong history -> xử lý như invalid
            invalid.append(str(number))

    # Một vé được coi là trúng thưởng nếu:
    # - Có ít nhất 5 số khớp (matched)
    # - Không có số nào chưa quay (not_drawn)
    # - Không có số không hợp lệ (invalid)
    is_winner = len(set(matched)) >= 5 and not not_drawn and not invalid

    lines = []

    if matched:
        matched_str = ", ".join(f"`{n}`" for n in sorted(set(matched)))
        lines.append(f"✅ *Số đã quay*: {matched_str}")

    if not_drawn:
        not_drawn_str = ", ".join(f"`{n}`" for n in sorted(set(not_drawn)))
        lines.append(f"⭕ *Số chưa quay*: {not_drawn_str}")

    if invalid:
        invalid_str = ", ".join(f"`{n}`" for n in sorted(set(invalid)))
        lines.append(f"⚠️ *Không hợp lệ / ngoài khoảng*: {invalid_str}")

    if is_winner:
        display_name = user.full_name or (user.username or str(user.id))
        winner_set = sorted(set(matched))
        winner_numbers = ", ".join(f"`{n}`" for n in winner_set)

        # Ghi lại thông tin người trúng vào session.winners
        if not hasattr(session, "winners"):
            session.winners = []
        session.winners.append(
            {
                "user_id": user.id,
                "name": display_name,
                "numbers": winner_set,
                "time": now.isoformat(timespec="seconds"),
            }
        )

        # Lưu lại session với vé trúng thưởng mới
        session_manager.persist_session(chat_id)

        lines.append(
            f"\n🏆 *Chúc mừng* {escape_markdown(display_name)} *\\!* \n"
            f"Vé của bạn là *TRÚNG THƯỞNG* với ít nhất *5 số* đã quay:\n"
            f"{winner_numbers}"
        )

    if not lines:
        lines.append("ℹ️ Không có kết quả để hiển thị. Kiểm tra lại cú pháp giúp nhé.")

    header = "📎 *Kết quả kiểm tra dãy số:*\n\n"
    await update.message.reply_text(
        header + "\n".join(lines),
        parse_mode='Markdown'
    )

    # Sau khi xử lý xong, cập nhật timestamp cooldown cho user
    last_check_time[key] = now


async def xoakinh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /xoa_kinh - xoá vé trúng thưởng gần nhất của chính mình trong game hiện tại"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    session = session_manager.get_session(chat_id)

    if not session:
        await update.message.reply_text(
            "❌ *Chưa có game nào trong chat\\!*",
            parse_mode="Markdown",
        )
        return

    if not getattr(session, "started", False):
        await update.message.reply_text(
            "⏱️ Game chưa bắt đầu hoặc đã bị xoá, không có vé nào để xoá.",
            parse_mode="Markdown",
        )
        return

    winners = list(getattr(session, "winners", []))
    if not winners:
        await update.message.reply_text(
            "ℹ️ Hiện chưa có vé nào được ghi nhận là *trúng thưởng*.",
            parse_mode="Markdown",
        )
        return

    # Tìm lần trúng gần nhất của chính user (từ cuối danh sách)
    idx_to_remove = None
    for i in range(len(winners) - 1, -1, -1):
        if winners[i].get("user_id") == user_id:
            idx_to_remove = i
            break

    if idx_to_remove is None:
        await update.message.reply_text(
            "ℹ️ Bạn hiện chưa có vé nào được ghi nhận là *trúng thưởng* trong game này.",
            parse_mode="Markdown",
        )
        return

    removed = winners.pop(idx_to_remove)
    session.winners = winners

    numbers = removed.get("numbers") or []
    numbers_str = ", ".join(f"`{n}`" for n in numbers)

    # Lưu lại sau khi xoá vé trúng
    session_manager.persist_session(chat_id)

    await update.message.reply_text(
        "✅ Đã xoá vé trúng thưởng gần nhất của bạn khỏi danh sách kết quả.\n\n"
        f"🧾 Vé vừa xoá: {numbers_str}" if numbers_str else "✅ Đã xoá vé trúng thưởng gần nhất của bạn.",
        parse_mode="Markdown",
    )


async def layve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /lay_ve - chọn / xem vé (mã màu) trước khi game bắt đầu"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    session = session_manager.get_session(chat_id)

    if not session:
        await update.message.reply_text(
            "❌ *Chưa có game nào trong chat\\!*\n\n"
            "Host dùng `/moi <tên_game>` hoặc `/pham_vi <x> <y>` để tạo game trước nhé\\.",
            parse_mode="Markdown",
        )
        return

    # Kiểm tra timeout session
    if not await ensure_active_session(update, chat_id, session):
        return

    # Khởi tạo cấu trúc vé nếu chưa có
    if not hasattr(session, "tickets"):
        session.tickets = {}
    if not hasattr(session, "user_tickets"):
        session.user_tickets = {}

    tickets: dict[str, int] = session.tickets
    user_tickets: dict[int, str] = session.user_tickets

    # Nếu game đã bắt đầu: không cho lấy/đổi vé nữa, chỉ thông báo
    if getattr(session, "started", False):
        current = user_tickets.get(user_id)
        if current:
            await update.message.reply_text(
                f"ℹ️ Game đã bắt đầu\\. Vé của bạn là: `{current}`\\. "
                "Không thể đổi vé nữa.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "ℹ️ Game đã bắt đầu và bạn chưa đăng ký vé nào\\. "
                "Không thể lấy vé mới nữa.",
                parse_mode="Markdown",
            )
        return

    # Không có tham số: liệt kê các vé và trạng thái
    if not context.args:
        lines: list[str] = []
        current = user_tickets.get(user_id)
        for code in TICKET_CODES:
            holder_id = tickets.get(code)
            if holder_id is None:
                status = "🟢 *Còn trống*"
            elif holder_id == user_id:
                status = "🧾 *Bạn đang giữ*"
            else:
                status = "🔴 *Đã có người lấy*"

            lines.append(f"- `{code}` → {status}")

        header = "🎟️ *Danh sách vé hiện có:*\n\n"
        if current:
            header += f"🧾 Vé hiện tại của bạn: `{current}`\n\n"
        else:
            header += "🧾 Bạn chưa chọn vé nào\\.\n\n"
        
        # Danh sách người đã lấy vé (user_id -> mã vé)
        people_lines: list[str] = []
        # Cố gắng lấy tên người chơi từ danh sách participants nếu có
        participants = []
        if hasattr(session, "get_participants"):
            try:
                participants = session.get_participants()
            except Exception:
                participants = []
        name_by_id: dict[int, str] = {}
        for p in participants:
            uid = p.get("user_id")
            name = p.get("name") or str(uid)
            if uid is not None:
                name_by_id[uid] = name

        for uid, code in user_tickets.items():
            display_name = name_by_id.get(uid, str(uid))
            people_lines.append(f"- {escape_markdown(display_name)}: `{code}`")

        if people_lines:
            header += "👥 *Danh sách người đã lấy vé:*\n" + "\n".join(people_lines) + "\n\n"

        header += "Dùng `/lay_ve <mã_vé>` để chọn hoặc đổi vé\\. Ví dụ: `/lay_ve tim1`"
        await update.message.reply_text(
            header + "\n" + "\n".join(lines),
            parse_mode="Markdown",
        )

        # Chỉ liệt kê, không thay đổi session -> không cần lưu
        return

    # Có tham số: cố gắng lấy / đổi vé
    code = context.args[0].lower()

    if code not in TICKET_CODES:
        await update.message.reply_text(
            "❌ *Mã vé không hợp lệ\\!*\n\n"
            f"Các vé hợp lệ: {', '.join(f'`{c}`' for c in TICKET_CODES)}",
            parse_mode="Markdown",
        )
        return

    holder_id = tickets.get(code)
    current = user_tickets.get(user_id)

    # Vé đang có người khác giữ
    if holder_id is not None and holder_id != user_id:
        await update.message.reply_text(
            f"⚠️ Vé `{code}` đã có người khác chọn rồi, bạn hãy chọn mã vé khác nhé.",
            parse_mode="Markdown",
        )
        return

    # Trả vé cũ nếu đang giữ vé khác
    if current and current != code:
        tickets.pop(current, None)

    # Gán vé mới cho user
    tickets[code] = user_id
    user_tickets[user_id] = code

    # Lưu session sau khi đổi vé
    session_manager.persist_session(chat_id)

    await update.message.reply_text(
        f"✅ Bạn đã chọn vé: `{code}`\n\n"
        "Nếu bạn gọi `/lay_ve <mã_vé_khác>` trước khi game bắt đầu, vé cũ sẽ được trả lại và thay bằng vé mới.",
        parse_mode="Markdown",
    )

    # Gửi ảnh vé tương ứng nếu có file
    image_path = TICKET_IMAGES.get(code)
    if image_path is not None and image_path.is_file():
        try:
            with open(image_path, "rb") as f:
                await update.message.reply_photo(
                    photo=f,
                    caption=f"🎟️ Vé của bạn: `{code}`",
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.error("Không thể gửi ảnh vé %s: %s", code, e)


def setup_bot(token: str) -> Application:
    """Setup và trả về Application instance"""
    application = Application.builder().token(token).build()
    
    # Register command handlers cơ bản
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))

    # Chỉ dùng các lệnh tiếng Việt thân thuộc cho game
    application.add_handler(CommandHandler("vong_moi", vongmoi_command))
    application.add_handler(CommandHandler("ket_thuc_vong", endround_command))
    application.add_handler(CommandHandler("moi", newsession_command))
    application.add_handler(CommandHandler("pham_vi", setrange_command))
    application.add_handler(CommandHandler("bat_dau", startsession_command))
    application.add_handler(CommandHandler("ket_thuc", endsession_command))
    application.add_handler(CommandHandler("tham_gia", join_command))
    application.add_handler(CommandHandler("danh_sach", players_command))
    application.add_handler(CommandHandler("lay_ve", layve_command))
    application.add_handler(CommandHandler("tra_ve", out_command))
    application.add_handler(CommandHandler("quay", spin_command))
    application.add_handler(CommandHandler("kinh", check_command))
    application.add_handler(CommandHandler("xoa_kinh", xoakinh_command))
    application.add_handler(CommandHandler("lich_su", history_command))
    application.add_handler(CommandHandler("trang_thai", status_command))
    application.add_handler(CommandHandler("dat_lai", reset_command))
    application.add_handler(CommandHandler("xoa", clear_command))
    application.add_handler(CommandHandler("ket_qua", lastresult_command))
    application.add_handler(CommandHandler("xep_hang", leaderboard_command))
    application.add_handler(CommandHandler("tro_giup", help_command))
    
    return application

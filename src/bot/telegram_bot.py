"""
Telegram bot handlers và commands 
""" 
import logging
from datetime import datetime
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

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Session manager (shared instance)
session_manager = SessionManager()

# Lưu kết quả game gần nhất theo chat: {chat_id: {...}}
last_results: dict[int, dict] = {}

# Thống kê wins/participations theo chat
stats: dict[int, dict] = {}

# Cooldown chống spam
COOLDOWN_SPIN_SECONDS = 2
COOLDOWN_CHECK_SECONDS = 2
last_spin_time: dict[int, datetime] = {}
last_check_time: dict[tuple[int, int], datetime] = {}


def escape_markdown(text: str) -> str:
    """Escape các ký tự đặc biệt trong Markdown"""
    # Escape các ký tự đặc biệt của Markdown
    special_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


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
            KeyboardButton("/newsession"),
            KeyboardButton("/join"),
            KeyboardButton("/players"),
        ],
        [
            KeyboardButton("/spin"),
            KeyboardButton("/check"),
            KeyboardButton("/status"),
        ],
        [
            KeyboardButton("/history"),
            KeyboardButton("/reset"),
        ],
        [
            KeyboardButton("/endsession"),
            KeyboardButton("/clear"),
            KeyboardButton("/help"),
        ],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )

    text = (
        "📋 *Menu thao tác nhanh*\n\n"
        "🕹️ *Game & người chơi*\n"
        "• `/newsession <tên_game>` \\- tạo game mới trong chat\n"
        "• `/startsession` \\- host bấm để *bắt đầu* game\n"
        "• `/join` \\- tham gia game hiện tại\n"
        "• `/players` \\- xem danh sách người chơi\n"
        "• `/out` \\- rời khỏi game (người thường)\n\n"
        "🎲 *Quay số & trạng thái*\n"
        "• `/spin` \\- quay số\n"
        "• `/check <dãy_số>` \\- kiểm tra vé, số đã/ chưa quay\n"
        "• `/status` \\- xem trạng thái hiện tại\n"
        "• `/history` \\- lịch sử quay gần đây\n\n"
        "⚙️ *Quản lý phiên chơi*\n"
        "• `/reset` \\- reset lại dãy số\n"
        "• `/endsession` \\- kết thúc game (chỉ host)\n"
        "• `/clear` \\- xoá session trong chat\n\n"
        "📊 *Thống kê & kết quả*\n"
        "• `/lastresult` \\- xem kết quả game gần nhất trong chat\n"
        "• `/leaderboard` \\- bảng xếp hạng trúng thưởng (mặc định)\n"
        "• `/leaderboard join` \\- bảng xếp hạng số game tham gia\n\n"
        "ℹ️ *Khác*\n"
        "• `/help` \\- hướng dẫn chi tiết\n\n"
        "_Chọn nhanh nút bên dưới rồi bổ sung tham số nếu cần, ví dụ:_\n"
        "• `/newsession Loto tối nay`\n"
        "• `/check 1 5 10 20`"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def newsession_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /newsession <tên_game>
    
    Tạo một session mới với tên game, sử dụng khoảng số mặc định 1 -> MAX_NUMBERS.
    """
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id

    if not context.args:
        await update.message.reply_text(
            "❌ *Sai cú pháp\\!*\n\n"
            "Sử dụng: `/newsession <tên_game>`\n"
            "Ví dụ: `/newsession Loto tối nay`",
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
        # Owner auto join
        session.add_participant(user_id=user_id, name=user.full_name or (user.username or str(user_id)))

        await update.message.reply_text(
            f"✅ *Đã tạo session mới\\!*\n\n"
            f"🕹️ Tên game: `{escape_markdown(game_name)}`\n"
            f"📊 Khoảng số: `1 -> {MAX_NUMBERS}`\n"
            f"📊 Tổng số: `{session.get_total_numbers()}`\n"
            f"⚙️ Loại bỏ sau khi quay: `{'Có' if session.remove_after_spin else 'Không'}`\n\n"
            f"Dùng `/spin` để quay và `/check <danh_sách_số>` để kiểm tra vé\\.",
            parse_mode='Markdown'
        )
    except ValueError as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")


async def setrange_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /setrange <x> <y>"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ *Sai cú pháp\\!*\n\n"
            "Sử dụng: `/setrange <x> <y>`\n"
            "Ví dụ: `/setrange 1 100`",
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
        session.add_participant(user_id=user_id, name=user.full_name or (user.username or str(user_id)))
        
        await update.message.reply_text(
            f"✅ *Đã tạo session\\!*\n\n"
            f"📊 Khoảng số: `{start_num} -> {end_num}`\n"
            f"📊 Tổng số: `{session.get_total_numbers()}`\n"
            f"⚙️ Loại bỏ sau khi quay: `{'Có' if session.remove_after_spin else 'Không'}`\n\n"
            f"Sử dụng `/spin` để quay wheel\\!",
            parse_mode='Markdown'
        )
    except ValueError as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")


async def spin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /spin"""
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
            "❌ *Chưa có session\\!*\n\n"
            "Sử dụng `/setrange <x> <y>` để tạo session trước\\.",
            parse_mode='Markdown'
        )
        return

    # Yêu cầu host đã /startsession trước khi quay
    if not getattr(session, "started", False):
        await update.message.reply_text(
            "⏱️ *Game chưa bắt đầu\\!* \n\n"
            "Host cần dùng lệnh `/startsession` để bắt đầu game trước khi quay số.",
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
    except ValueError as e:
        await update.message.reply_text(f"❌ {str(e)}")


async def toggle_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /toggle_remove"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)
    
    if not session:
        await update.message.reply_text(
            "❌ *Chưa có session\\!*\n\n"
            "Sử dụng `/setrange <x> <y>` để tạo session trước\\.",
            parse_mode='Markdown'
        )
        return
    
    # Toggle remove mode
    new_mode = not session.remove_after_spin
    set_remove_mode(session, new_mode)
    
    mode_text = "Có" if new_mode else "Không"
    await update.message.reply_text(
        f"⚙️ *Chế độ loại bỏ:* `{mode_text}`\n\n"
        f"{'✅ Số đã quay sẽ bị loại bỏ' if new_mode else '✅ Số đã quay vẫn có thể xuất hiện lại'}",
        parse_mode='Markdown'
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /reset"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)
    
    if not session:
        await update.message.reply_text(
            "❌ *Chưa có session\\!*\n\n"
            "Sử dụng `/setrange <x> <y>` để tạo session trước\\.",
            parse_mode='Markdown'
        )
        return
    
    reset_session(session)
    await update.message.reply_text(
        f"🔄 *Đã reset\\!*\n\n"
        f"📊 Danh sách đã được khôi phục về ban đầu\\.\n"
        f"📊 Số còn lại: `{session.get_remaining_count()}/{session.get_total_numbers()}`",
        parse_mode='Markdown'
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /status"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)
    
    if not session:
        await update.message.reply_text(
            "❌ *Chưa có session\\!*\n\n"
            "Sử dụng `/setrange <x> <y>` để tạo session trước\\.",
            parse_mode='Markdown'
        )
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
    """Handler cho lệnh /history - hiển thị lịch sử quay gần đây"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)
    
    if not session:
        await update.message.reply_text(
            "❌ *Chưa có session\\!*\n\n"
            "Sử dụng `/setrange <x> <y>` để tạo session trước\\.",
            parse_mode='Markdown'
        )
        return
    
    history = session.get_recent_history(limit=10)
    if not history:
        await update.message.reply_text(
            "ℹ️ Chưa có lịch sử quay nào.",
            parse_mode='Markdown'
        )
        return
    
    lines = []
    # Hiển thị từ lần quay mới nhất trở về trước
    for idx, item in enumerate(reversed(history), start=1):
        number = item.get("number")
        time_str = item.get("time")
        lines.append(f"{idx}. `{number}` (lúc {time_str})")
    
    message = "📜 *Lịch sử quay gần đây:*\n\n" + "\n".join(lines)
    await update.message.reply_text(message, parse_mode='Markdown')


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /clear"""
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
        "Sử dụng `/newsession <tên_game>` hoặc `/setrange <x> <y>` để tạo session mới\\.",
        parse_mode='Markdown'
    )


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /join - cho phép người khác tham gia game hiện tại trong nhóm/chat"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    session = session_manager.get_session(chat_id)

    if not session:
        await update.message.reply_text(
            "❌ *Chưa có game nào đang chạy trong chat này\\!*\n\n"
            "Dùng `/newsession <tên_game>` để tạo game mới.",
            parse_mode='Markdown'
        )
        return

    display_name = user.full_name or (user.username or str(user_id))
    is_new = session.add_participant(user_id=user_id, name=display_name)

    game_name = getattr(session, "game_name", None)
    if is_new:
        text = "✅ Bạn đã tham gia game hiện tại."
    else:
        text = "ℹ️ Bạn đã ở trong danh sách người chơi."

    if game_name:
        text = f"{text}\n\n🕹️ Game: `{escape_markdown(game_name)}`"

    await update.message.reply_text(text, parse_mode='Markdown')


async def out_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /out - cho phép người chơi rời khỏi game"""
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
            "⏱️ Game đã bắt đầu, không thể dùng `/out` để rời game nữa.",
            parse_mode='Markdown'
        )
        return

    # Host không được out, phải dùng /endsession
    if getattr(session, "owner_id", None) == user_id:
        await update.message.reply_text(
            "❌ Bạn là chủ phòng\\. Dùng `/endsession` để kết thúc game thay vì `/out`.",
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
    """Handler cho lệnh /players - hiển thị danh sách người tham gia game"""
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


async def startsession_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /startsession - host bấm để bắt đầu game"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    session = session_manager.get_session(chat_id)

    if not session:
        await update.message.reply_text(
            "❌ *Chưa có session nào để bắt đầu\\!* \n\n"
            "Dùng `/newsession <tên_game>` hoặc `/setrange <x> <y>` để tạo game trước.",
            parse_mode='Markdown'
        )
        return

    owner_id = getattr(session, "owner_id", None)
    if owner_id is not None and owner_id != user_id:
        await update.message.reply_text(
            "❌ Chỉ *host* (người tạo game) mới được quyền bắt đầu game bằng `/startsession`.",
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

    game_name = getattr(session, "game_name", None)
    if game_name:
        text = (
            f"🚀 *Game đã bắt đầu\\!* \n\n"
            f"🕹️ `{escape_markdown(game_name)}`\n\n"
            "Mọi người có thể dùng:\n"
            "• `/spin` để quay số\n"
            "• `/check <dãy_số>` để kiểm tra vé"
        )
    else:
        text = (
            "🚀 *Game đã bắt đầu\\!* \n\n"
            "Mọi người có thể dùng:\n"
            "• `/spin` để quay số\n"
            "• `/check <dãy_số>` để kiểm tra vé"
        )

    await update.message.reply_text(text, parse_mode='Markdown')


async def lastresult_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /lastresult - hiển thị kết quả game gần nhất trong chat"""
    chat_id = update.effective_chat.id
    data = last_results.get(chat_id)

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
    """Handler cho lệnh /leaderboard - bảng xếp hạng trúng thưởng / tham gia"""
    chat_id = update.effective_chat.id
    chat_stats = stats.get(chat_id)

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
            key=lambda kv: kv[1].get("count", 0),
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
            key=lambda kv: kv[1].get("count", 0),
            reverse=True
        )[:10]
        title = "👥 *Top người tham gia nhiều game nhất:*"

    lines = []
    for idx, (uid, info) in enumerate(sorted_items, start=1):
        name = escape_markdown(str(info.get("name") or uid))
        count = info.get("count", 0)
        lines.append(f"{idx}. {name} - `{count}` lần")

    mode_hint = (
        "\n\nℹ️ Dùng `/leaderboard wins` hoặc `/leaderboard join` để xem bảng xếp hạng tương ứng."
    )

    await update.message.reply_text(
        f"{title}\n\n" + "\n".join(lines) + mode_hint,
        parse_mode='Markdown'
    )


async def endsession_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /endsession
    
    Chỉ người đã tạo session (/newsession hoặc /setrange) mới được phép kết thúc.
    """
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    session = session_manager.get_session(chat_id)

    if not session:
        await update.message.reply_text(
            "ℹ️ Không có session nào đang hoạt động để kết thúc.",
            parse_mode='Markdown'
        )
        return

    # Nếu có gắn owner_id thì kiểm tra, mặc dù hiện tại session được map theo user_id
    owner_id = getattr(session, "owner_id", user_id)
    if owner_id != user_id:
        await update.message.reply_text(
            "❌ Chỉ người tạo session mới được quyền kết thúc (/endsession).",
            parse_mode='Markdown'
        )
        return

    game_name = getattr(session, "game_name", None)

    # Cập nhật thống kê số lần tham gia dựa trên participants
    chat_stats = stats.setdefault(chat_id, {"wins": {}, "participations": {}})
    participations = chat_stats["participations"]
    for p in session.get_participants():
        uid = p.get("user_id")
        if uid is None:
            continue
        name = p.get("name") or str(uid)
        info = participations.get(uid, {"count": 0, "name": name})
        info["count"] += 1
        info["name"] = name
        participations[uid] = info

    # Lưu kết quả game gần nhất cho chat này
    host_name = user.full_name or (user.username or str(user_id))
    last_results[chat_id] = {
        "game_name": game_name,
        "host_id": user_id,
        "host_name": host_name,
        "numbers_drawn": list(session.history),
        "winners": list(getattr(session, "winners", [])),
        "ended_at": datetime.now().isoformat(timespec="seconds"),
    }

    session_manager.delete_session(chat_id)

    if game_name:
        msg = (
            f"🛑 *Đã kết thúc session game* `{escape_markdown(game_name)}`\\.\n\n"
            "Bạn có thể tạo game mới bằng `/newsession <tên_game>`."
        )
    else:
        msg = (
            "🛑 *Đã kết thúc session hiện tại\\!* \n\n"
            "Bạn có thể tạo game mới bằng `/newsession <tên_game>`."
        )

    await update.message.reply_text(msg, parse_mode='Markdown')


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /check <danh_sách_số>
    
    Ví dụ: /check 1 2 3 10 20
            /check 1,5,10,15
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
            "⏱️ Bạn vừa /check xong, đợi vài giây rồi thử lại nhé.",
            parse_mode='Markdown'
        )
        return

    if not session:
        await update.message.reply_text(
            "❌ *Chưa có session\\!*\n\n"
            "Sử dụng `/newsession <tên_game>` hoặc `/setrange <x> <y>` để tạo session trước\\.",
            parse_mode='Markdown'
        )
        return

    # Yêu cầu game đã được host /startsession
    if not getattr(session, "started", False):
        await update.message.reply_text(
            "⏱️ *Game chưa bắt đầu\\!* \n\n"
            "Host cần dùng lệnh `/startsession` để bắt đầu game trước khi kiểm tra vé.",
            parse_mode='Markdown'
        )
        return

    if not context.args:
        await update.message.reply_text(
            "❌ *Sai cú pháp\\!*\n\n"
            "Sử dụng: `/check <danh_sách_số>`\n"
            "Ví dụ: `/check 1 2 3 10 20` hoặc `/check 1,5,10,15`",
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
    # - Có ít nhất 4 số khớp (matched)
    # - Không có số nào chưa quay (not_drawn)
    # - Không có số không hợp lệ (invalid)
    is_winner = len(set(matched)) >= 4 and not not_drawn and not invalid

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

        # Cập nhật thống kê wins cho leaderboard
        chat_stats = stats.setdefault(chat_id, {"wins": {}, "participations": {}})
        wins = chat_stats["wins"]
        info = wins.get(user.id, {"count": 0, "name": display_name})
        info["count"] += 1
        info["name"] = display_name
        wins[user.id] = info

        lines.append(
            f"\n🏆 *Chúc mừng* {escape_markdown(display_name)} *\\!* \n"
            f"Vé của bạn là *TRÚNG THƯỞNG* với ít nhất *4 số* đã quay:\n"
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


def setup_bot(token: str) -> Application:
    """Setup và trả về Application instance"""
    application = Application.builder().token(token).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("newsession", newsession_command))
    application.add_handler(CommandHandler("startsession", startsession_command))
    application.add_handler(CommandHandler("endsession", endsession_command))
    application.add_handler(CommandHandler("lastresult", lastresult_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    application.add_handler(CommandHandler("join", join_command))
    application.add_handler(CommandHandler("out", out_command))
    application.add_handler(CommandHandler("players", players_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("setrange", setrange_command))
    application.add_handler(CommandHandler("spin", spin_command))
    application.add_handler(CommandHandler("toggle_remove", toggle_remove_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("clear", clear_command))
    
    return application

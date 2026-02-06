""" 
Telegram bot handlers và commands 
""" 
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
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

# Map mã vé -> tên hiển thị (tiếng Việt)
TICKET_DISPLAY_NAMES: dict[str, str] = {
    "cam1": "Cam số 1",
    "cam2": "Cam số 2",
    "do1": "Đổ số 1",
    "do2": "Đổ số 2",
    "duong1": "Xanh dương số 1",
    "duong2": "Xanh dương số 2",
    "hong1": "Hồng số 1",
    "hong2": "Hồng số 2",
    "luc1": "Xanh lục số 1",
    "luc2": "Xanh lục số 2",
    "tim1": "Tím số 1",
    "tim2": "Tím số 2",
    "vang1": "Vàng số 1",
    "vang2": "Vàng số 2",
    "xanh1": "Xanh số 1",
    "xanh2": "Xanh số 2",
}


def ticket_display_name(code: str) -> str:
    """Trả về tên hiển thị của vé, hoặc mã gốc nếu không có map."""
    return TICKET_DISPLAY_NAMES.get(code, code)


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

    target_chat_id = chat_id
    suffix = f":{target_chat_id}"

    await update.message.reply_text(
        f"✅ *Đã tạo vòng chơi mới\\!* \n\n"
        f"🔄 Tên vòng: `{escape_markdown(round_name)}`\n\n"
        "Giờ bạn có thể dùng các nút bên dưới hoặc lệnh gõ:\n"
        "• `/moi <tên_game>` để tạo ván game\n"
        "• `/ket_thuc_vong` để kết thúc vòng chơi",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🕹️ Tạo Game", callback_data=f"cmd:moi_input{suffix}"),
                InlineKeyboardButton("🏁 Kết thúc Vòng", callback_data=f"cmd:ket_thuc_vong{suffix}"),
            ]
        ])
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
    """Handler cho lệnh /menu - hiển thị menu phím bấm nhanh (Inboxed if in group)"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Text menu rút gọn và trực quan
    text = (
        "📋 *Bảng điều khiển Loto*\n\n"
        "🕹️ *Quản lý Game*\n"
        "• `/moi` \\- Tạo game mới\n"
        "• `/bat_dau` \\- Bắt đầu game\n"
        "• `/ket_thuc` \\- Kết thúc game\n\n"
        "🎟️ *Người chơi*\n"
        "• `/lay_ve` \\- Chọn màu vé\n"
        "• `/danh_sach` \\- Xem người chơi\n"
        "• `/tra_ve` \\- Rời game\n\n"
        "🎲 *Thao tác*\n"
        "• `/quay` \\- Quay số mới\n"
        "• `/kinh` \\- Kiểm tra vé\n"
        "• `/trang_thai` \\- Xem tiến độ\n"
        "• `/lich_su` \\- Xem các số đã ra"
    )

    # Nhận diện chat_id để nhúng vào nút bấm (để điều khiển từ xa khi gửi vào PM)
    target_chat_id = chat.id
    suffix = f":{target_chat_id}"

    # Inline Keyboard cho Menu - Nhúng ID nhóm vào callback
    keyboard = [
        [
            InlineKeyboardButton("🆕 Vòng mới", callback_data=f"cmd:vong_moi_input{suffix}"),
            InlineKeyboardButton("🏁 Kết thúc Vòng", callback_data=f"cmd:ket_thuc_vong{suffix}"),
        ],
        [
            InlineKeyboardButton("🕹️ Tạo Game", callback_data=f"cmd:moi_input{suffix}"),
            InlineKeyboardButton("🛑 Kết thúc Game", callback_data=f"cmd:ket_thuc{suffix}"),
        ],
        [
            InlineKeyboardButton("🎟️ Lấy vé", callback_data=f"cmd:lay_ve{suffix}"),
            InlineKeyboardButton("📊 Trạng thái", callback_data=f"cmd:trang_thai{suffix}"),
        ],
        [
            InlineKeyboardButton("� Quay số", callback_data=f"cmd:quay{suffix}"),
            InlineKeyboardButton("�🏆 Xếp hạng", callback_data=f"cmd:xep_hang{suffix}"),
        ],
        [
            InlineKeyboardButton("❓ Trợ giúp", callback_data=f"cmd:tro_giup{suffix}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Nếu đang ở trong nhóm/supergroup
    if chat.type in ["group", "supergroup"]:
        try:
            # Gửi tin nhắn riêng cho user
            await context.bot.send_message(
                chat_id=user.id,
                text=text + "\n\n⚠️ *Lưu ý:* Menu này chỉ mình bạn thấy và dùng để điều khiển game trong nhóm.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            # Thông báo trong nhóm
            await update.message.reply_text(
                f"📥 {user.mention_markdown()}\\!, tôi đã gửi Menu điều khiển riêng cho bạn\\. Hãy kiểm tra tin nhắn chờ nhé\\!",
                parse_mode="Markdown"
            )
        except Exception as e:
            # Nếu user chưa bao giờ chat với bot -> Bot không thể chủ động nhắn tin
            await update.message.reply_text(
                f"❌ {user.mention_markdown()}\\!, tôi không thể gửi tin nhắn riêng cho bạn\\.\n\n"
                f"Vui lòng nhấn vào @{context.bot.username} và bấm *Bắt đầu (Start)* trước, sau đó thử lại `/menu`\\.",
                parse_mode="Markdown"
            )
    else:
        # Nếu đang ở chat riêng với bot
        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
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

        target_chat_id = chat_id
        suffix = f":{target_chat_id}"

        await update.message.reply_text(
            f"✅ *Đã tạo game mới\\!*\n\n"
            f"🕹️ Tên game: `{escape_markdown(game_name)}`\n"
            f"📊 Khoảng số: `1 -> {MAX_NUMBERS}`\n"
            f"📊 Tổng số: `{session.get_total_numbers()}`\n"
            f"⚙️ Loại bỏ sau khi quay: `{'Có' if session.remove_after_spin else 'Không'}`\n\n"
            "Người chơi chọn vé bằng nút `/lay_ve` bên dưới.\n"
            "Host bấm `/bat_dau` khi mọi người đã sẵn sàng.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎟️ Lấy vé", callback_data=f"cmd:lay_ve{suffix}"), 
                 InlineKeyboardButton("👥 Danh sách", callback_data=f"cmd:danh_sach{suffix}")],
                [InlineKeyboardButton("🚀 Bắt đầu Game", callback_data=f"cmd:bat_dau{suffix}")]
            ])
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
        
        # Tự động nhúng chat_id vào nút bấm để hỗ trợ Quay tiếp từ xa (Inbox)
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"
        
        # Format message
        message = f"🎲 *Số được chọn: `{number}`*\n\n"
        message += f"📊 Còn lại: `{session.get_remaining_count()}/{session.get_total_numbers()}`"
        
        keyboard = [[InlineKeyboardButton("🎲 Quay tiếp", callback_data=f"cmd:quay{suffix}")]]
        if session.is_empty():
            message += "\n\n⚠️ Danh sách đã hết\\! Sử dụng `/reset` để làm mới\\."
            keyboard = [[InlineKeyboardButton("🔄 Reset số", callback_data=f"cmd:dat_lai{suffix}")]]
        
        # Thêm nút kiểm tra vé cho người chơi
        keyboard.append([InlineKeyboardButton("🧾 Kiểm tra vé (/kinh)", switch_inline_query_current_chat="/kinh ")])

        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

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
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Quay ngay", callback_data="cmd:quay")]
        ])
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
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🕹️ Tạo game mới", callback_data="cmd:moi")]
        ])
    )


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /tham_gia - chuyển hướng sang lấy vé (mọi người phải lấy vé trước khi chơi)"""
    session = session_manager.get_session(update.effective_chat.id)
    if not session:
        await update.message.reply_text(
            "❌ *Chưa có game nào đang chạy trong chat này\\!*\n\n"
            "Host dùng `/moi <tên_game>` để tạo game mới.",
            parse_mode='Markdown'
        )
        return
    await update.message.reply_text(
        "🎟️ *Để chơi, bạn cần lấy vé trước\\!*\n\n"
        "Bấm nút **Lấy vé** bên dưới để chọn màu vé của bạn\\.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎟️ Chọn vé ngay", callback_data="cmd:lay_ve")]
        ])
    )


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

    # Trả vé nếu đang giữ (giải phóng mã vé cho người khác)
    user_tickets = getattr(session, "user_tickets", {})
    tickets = getattr(session, "tickets", {})
    code = user_tickets.pop(user_id, None)
    if code is not None and code in tickets:
        tickets.pop(code, None)
        session_manager.persist_session(chat_id)

    removed = session.remove_participant(user_id)
    if removed:
        session_manager.persist_session(chat_id)
    if removed or code is not None:
        await update.message.reply_text(
            "✅ Bạn đã trả vé và rời khỏi game hiện tại.",
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
            "ℹ️ Hiện chưa có ai lấy vé / tham gia game.",
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

    header = "👥 *Danh sách người đã lấy vé (tham gia game):*\n\n"
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

    await update.message.reply_text(
        text, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Quay số đầu tiên", callback_data="cmd:quay")]
        ])
    )


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
                "ℹ️ Chưa có ai lấy vé / tham gia game trong chat này.",
                parse_mode='Markdown'
            )
            return
        sorted_items = sorted(
            participations.items(),
            key=lambda kv: kv[1].get("count", 0.0),
            reverse=True
        )[:10]
        title = "👥 *Top người lấy vé / tham gia nhiều game nhất:*"

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

    # Bắt buộc phải lấy vé trước khi chơi (kiểm tra vé)
    user_tickets = getattr(session, "user_tickets", {})
    if user.id not in user_tickets:
        await update.message.reply_text(
            "🎟️ *Bạn cần lấy vé trước khi chơi\\!*\n\n"
            "Dùng `/lay_ve <mã_vé>` để lấy vé\\. Ví dụ: `/lay_ve tim1`",
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
                f"ℹ️ Game đã bắt đầu\\. Vé của bạn là: {escape_markdown(ticket_display_name(current))}\\. "
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

    # Khám phá xem có đang điều khiển từ xa không (từ Inbox)
    is_remote = False
    target_chat_id = chat_id
    if update.effective_chat.type == "private":
        # Nếu đang ở private chat, ta kiểm tra xem có target_chat_id nào được truyền qua context không?
        # Hoặc đơn giản là dùng chat_id hiện tại (đã được generic_command_callback fake)
        is_remote = True
        target_chat_id = chat_id

    # Không có tham số: liệt kê các vé và trạng thái
    if not context.args:
        lines: list[str] = []
        current = user_tickets.get(user_id)
        
        # Suffix cho callback_data nếu là remote
        suffix = f":{target_chat_id}" if is_remote else ""
        
        for code in TICKET_CODES:
            holder_id = tickets.get(code)
            if holder_id is None:
                status = "🟢 *Còn trống*"
            elif holder_id == user_id:
                status = "🧾 *Bạn đang giữ*"
            else:
                status = "🔴 *Đã có người lấy*"

            lines.append(f"- {escape_markdown(ticket_display_name(code))} → {status}")

        header = "🎟️ *Danh sách vé hiện có:*\n\n"
        if current:
            header += f"🧾 Vé hiện tại của bạn: {escape_markdown(ticket_display_name(current))}\n\n"
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
            people_lines.append(f"- {escape_markdown(display_name)}: {escape_markdown(ticket_display_name(code))}")

        if people_lines:
            header += "👥 *Danh sách người đã lấy vé:*\n" + "\n".join(people_lines) + "\n\n"

        header += "Chọn vé bên dưới hoặc gõ `/lay_ve <mã_vé>`\\. Ví dụ: `/lay_ve tim1`"
        # Inline Keyboard: 4 cột, mỗi nút = một vé
        keyboard = []
        row = []
        for i, code in enumerate(TICKET_CODES):
            holder_id = tickets.get(code)
            display = ticket_display_name(code)
            if holder_id is None:
                label = display
            elif holder_id == user_id:
                label = f"✅ {display}"
            else:
                label = f"🔴 {display}"

            row.append(InlineKeyboardButton(label, callback_data=f"lay_ve:{code}{suffix}"))
            if len(row) == 4 or i == len(TICKET_CODES) - 1:
                keyboard.append(row)
                row = []
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            header + "\n" + "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )

        # Chỉ liệt kê, không thay đổi session -> không cần lưu
        return

    # Có tham số: cố gắng lấy / đổi vé
    code = context.args[0].lower()

    if code not in TICKET_CODES:
        valid_list = ", ".join(f"{escape_markdown(ticket_display_name(c))} (`{c}`)" for c in TICKET_CODES)
        await update.message.reply_text(
            "❌ *Mã vé không hợp lệ\\!*\n\n"
            f"Các vé hợp lệ: {valid_list}",
            parse_mode="Markdown",
        )
        return

    holder_id = tickets.get(code)
    current = user_tickets.get(user_id)

    # Vé đang có người khác giữ
    if holder_id is not None and holder_id != user_id:
        await update.message.reply_text(
            f"⚠️ Vé {escape_markdown(ticket_display_name(code))} đã có người khác chọn rồi, bạn hãy chọn mã vé khác nhé.",
            parse_mode="Markdown",
        )
        return

    # Trả vé cũ nếu đang giữ vé khác
    if current and current != code:
        tickets.pop(current, None)

    # Gán vé mới cho user
    tickets[code] = user_id
    user_tickets[user_id] = code

    # Lấy vé = tham gia game: thêm vào danh sách người chơi nếu chưa có
    display_name = user.full_name or (user.username or str(user_id))
    session.add_participant(user_id=user_id, name=display_name)

    # Lưu session sau khi đổi vé
    session_manager.persist_session(chat_id)

    # Hiển thị danh sách người đã lấy vé
    participants = []
    if hasattr(session, "get_participants"):
        try:
            participants = session.get_participants()
        except Exception:
            participants = []
    name_by_id = {p.get("user_id"): (p.get("name") or str(p.get("user_id"))) for p in participants if p.get("user_id") is not None}
    people_lines = [f"- {escape_markdown(name_by_id.get(uid, str(uid)))}: {escape_markdown(ticket_display_name(c))}" for uid, c in user_tickets.items()]
    list_text = "👥 *Danh sách người đã lấy vé:*\n" + "\n".join(people_lines) if people_lines else ""

    success_msg = (
        f"✅ Bạn đã lấy vé: {escape_markdown(ticket_display_name(code))} và tham gia game.\n\n"
        "Nếu bạn gọi `/lay_ve <mã_vé_khác>` trước khi game bắt đầu, vé cũ sẽ được trả lại và thay bằng vé mới."
    )
    if list_text:
        success_msg += "\n\n" + list_text

    await update.message.reply_text(success_msg, parse_mode="Markdown")

    # Gửi ảnh vé tương ứng nếu có file
    image_path = TICKET_IMAGES.get(code)
    if image_path is not None and image_path.is_file():
        try:
            with open(image_path, "rb") as f:
                await update.message.reply_photo(
                    photo=f,
                    caption=f"🎟️ Vé của bạn: {escape_markdown(ticket_display_name(code))}",
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.error("Không thể gửi ảnh vé %s: %s", code, e)

async def lay_ve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi user bấm nút chọn vé trên Inline Keyboard (hỗ trợ remote chat_id)"""
    query = update.callback_query
    # data format: "lay_ve:tim1" hoặc "lay_ve:tim1:-chat_id"
    data_parts = query.data.split(":")
    try:
        code = data_parts[1]
        # Nếu có chat_id đính kèm (remote mode)
        chat_id = int(data_parts[2]) if len(data_parts) > 2 else query.message.chat_id
    except (IndexError, ValueError):
        await query.answer("Lỗi dữ liệu vé.")
        return

    user = query.from_user
    user_id = user.id
    
    session = session_manager.get_session(chat_id)
    if not session:
        await query.answer("❌ Chưa có game nào đang chạy.", show_alert=True)
        return

    # Khởi tạo cấu trúc vé nếu chưa có
    if not hasattr(session, "tickets"):
        session.tickets = {}
    if not hasattr(session, "user_tickets"):
        session.user_tickets = {}

    tickets = session.tickets
    user_tickets = session.user_tickets

    # Nếu game đã bắt đầu: không cho lấy/đổi vé nữa
    if getattr(session, "started", False):
        await query.answer("⏱️ Game đã bắt đầu, không thể lấy/đổi vé nữa.", show_alert=True)
        return

    holder_id = tickets.get(code)
    current = user_tickets.get(user_id)

    # Vé đang có người khác giữ
    if holder_id is not None and holder_id != user_id:
        await query.answer(f"⚠️ Vé {ticket_display_name(code)} đã có người khác chọn rồi.", show_alert=True)
        return
        
    # Nếu bấm vào vé mình đang giữ
    if holder_id == user_id:
        await query.answer(f"🧾 Bạn đang giữ vé {ticket_display_name(code)} rồi.")
        return

    # Trả vé cũ nếu đang giữ vé khác
    if current and current != code:
        tickets.pop(current, None)

    # Gán vé mới cho user
    tickets[code] = user_id
    user_tickets[user_id] = code

    # Lấy vé = tham gia game: thêm vào danh sách người chơi nếu chưa có
    display_name = user.full_name or (user.username or str(user_id))
    session.add_participant(user_id=user_id, name=display_name)

    # Lưu session sau khi đổi vé
    session_manager.persist_session(chat_id)

    # Trả lời nhanh
    await query.answer(f"✅ Đã chọn {ticket_display_name(code)}!")

    # Build danh sách người đã lấy vé
    participants = []
    if hasattr(session, "get_participants"):
        try:
            participants = session.get_participants()
        except Exception:
            participants = []
    name_by_id = {p.get("user_id"): (p.get("name") or str(p.get("user_id"))) for p in participants if p.get("user_id") is not None}
    people_lines = [f"- {escape_markdown(name_by_id.get(uid, str(uid)))}: {escape_markdown(ticket_display_name(c))}" for uid, c in user_tickets.items()]
    list_text = "👥 *Danh sách người đã lấy vé:*\n" + "\n".join(people_lines) if people_lines else ""

    success_msg = (
        f"✅ {escape_markdown(display_name)} đã lấy vé: {escape_markdown(ticket_display_name(code))} và tham gia game.\n\n"
        "Nếu bạn chọn mã vé khác trước khi game bắt đầu, vé cũ sẽ được trả lại và thay bằng vé mới."
    )
    if list_text:
        success_msg += "\n\n" + list_text

    await query.message.reply_text(success_msg, parse_mode="Markdown")

    # Gửi ảnh vé tương ứng nếu có file
    image_path = TICKET_IMAGES.get(code)
    if image_path is not None and image_path.is_file():
        try:
            with open(image_path, "rb") as f:
                await query.message.reply_photo(
                    photo=f,
                    caption=f"🎟️ Vé của bạn: {escape_markdown(ticket_display_name(code))}",
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.error("Không thể gửi ảnh vé %s: %s", code, e)

    # Cập nhật lại phím bấm ở message cũ (hỗ trợ remote suffix)
    keyboard = []
    row = []
    # Xác định suffix cho các nút bấm (giống logic ở đầu hàm)
    is_remote_kb = (chat_id != query.message.chat_id)
    kb_suffix = f":{chat_id}" if is_remote_kb else ""

    for i, c in enumerate(TICKET_CODES):
        h_id = tickets.get(c)
        disp = ticket_display_name(c)
        if h_id is None:
            lbl = disp
        elif h_id == user_id:
            lbl = f"✅ {disp}"
        else:
            lbl = f"🔴 {disp}"

        row.append(InlineKeyboardButton(lbl, callback_data=f"lay_ve:{c}{kb_suffix}"))
        if len(row) == 4 or i == len(TICKET_CODES) - 1:
            keyboard.append(row)
            row = []
    
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))


async def generic_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý các lệnh từ nút bấm trong Menu (hỗ trợ điều khiển từ xa qua chat_id nhúng)"""
    query = update.callback_query
    data = query.data
    
    if not data.startswith("cmd:"):
        return
        
    # data format: "cmd:action:target_chat_id"
    parts = data.split(":")
    command = parts[1]
    
    # Nếu có target_chat_id nhúng trong nút bấm
    target_chat_id = int(parts[2]) if len(parts) > 2 else query.message.chat_id
    
    # Tạo một Update "giả" để truyền chat_id mục tiêu vào các handler
    # Telegram-python-bot dùng effective_chat, effective_user để xử lý
    # Ta sẽ ghi đè tạm thời các thuộc tính này
    
    class MockMessage:
        def __init__(self, original_msg, target_id):
            self.chat = original_msg.chat
            self.chat_id = target_id
            self.from_user = original_msg.from_user
            self.text = f"/{command}"
            self.reply_to_message = original_msg.reply_to_message
            self.message_id = original_msg.message_id
        
        async def reply_text(self, *args, **kwargs):
            # Nếu lệnh thành công, bot nên reply vào nhóm nếu là lệnh public như /quay
            # Nhưng ở đây để đơn giản, ta reply trực tiếp vào chat hiện tại (PM) để người dùng thấy kết quả
            return await query.message.reply_text(*args, **kwargs)
        
        async def reply_photo(self, *args, **kwargs):
            return await query.message.reply_photo(*args, **kwargs)

    # Tạo đối tượng Update giả lập để tránh lỗi "AttributeError: can't set attribute"
    mock_message = MockMessage(query.message, target_chat_id)
    mock_chat = type('MockChat', (), {'id': target_chat_id, 'type': 'supergroup'})()
    
    class ProxyUpdate:
        def __init__(self, original, message, chat):
            self.message = message
            self.effective_message = message
            self.effective_chat = chat
            self.effective_user = original.effective_user
            self.callback_query = original.callback_query
            # Một số handler có thể dùng các thuộc tính private
            self._effective_chat = chat
            self._effective_user = original.effective_user
            
    mock_update = ProxyUpdate(update, mock_message, mock_chat)
    
    try:
        if command == "lay_ve":
            await layve_command(mock_update, context)
        elif command == "danh_sach":
            await players_command(mock_update, context)
        elif command == "bat_dau":
            await startsession_command(mock_update, context)
        elif command == "ket_thuc":
            await endsession_command(mock_update, context)
        elif command == "quay":
            await spin_command(mock_update, context)
        elif command == "dat_lai":
            await reset_command(mock_update, context)
        elif command == "xep_hang":
            await leaderboard_command(mock_update, context)
        elif command == "trang_thai":
            await status_command(mock_update, context)
        elif command == "tro_giup":
            await help_command(mock_update, context)
        elif command == "vong_moi_input":
            from telegram import ForceReply
            await query.message.reply_text(
                f"📝 *Tạo Vòng mới cho nhóm {target_chat_id}*\n\nHãy nhập tên vòng chơi mới của bạn:",
                parse_mode="Markdown",
                reply_markup=ForceReply(selective=True)
            )
            context.user_data["pending_action"] = "vong_moi"
            context.user_data["target_chat_id"] = target_chat_id
        elif command == "moi_input":
            from telegram import ForceReply
            await query.message.reply_text(
                f"📝 *Tạo Game mới cho nhóm {target_chat_id}*\n\nHãy nhập tên ván game mới:",
                parse_mode="Markdown",
                reply_markup=ForceReply(selective=True)
            )
            context.user_data["pending_action"] = "moi"
            context.user_data["target_chat_id"] = target_chat_id
        elif command == "ket_thuc_vong":
            await endround_command(mock_update, context)
        
        await query.answer()
    except Exception as e:
        logger.error(f"Error in generic_command_callback: {e}")
        await query.answer("Có lỗi xảy ra khi thực hiện lệnh.", show_alert=True)

async def handle_force_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi user reply lại tin nhắn nhập tên Vòng/Game"""
    if not update.message or not update.message.text:
        return
        
    action = context.user_data.get("pending_action")
    target_chat_id = context.user_data.get("target_chat_id")
    
    if not action or not target_chat_id:
        return
        
    text = update.message.text.strip()
    
    # Sử dụng ProxyUpdate để tránh lỗi can't set attribute
    class ProxyUpdate:
        def __init__(self, original, chat_id):
            self.message = original.message
            self.effective_message = original.message
            self.effective_chat = type('MockChat', (), {'id': chat_id, 'type': 'supergroup'})()
            self.effective_user = original.effective_user
            # Thuộc tính private if any
            self._effective_chat = self.effective_chat
            self._effective_user = original.effective_user
            
    mock_update = ProxyUpdate(update, target_chat_id)
    context.args = [text] 
    
    try:
        if action == "vong_moi":
            await vongmoi_command(mock_update, context)
        elif action == "moi":
            await newsession_command(mock_update, context)
            
        # Xoá trạng thái chờ
        del context.user_data["pending_action"]
        del context.user_data["target_chat_id"]
    except Exception as e:
        logger.error(f"Error in handle_force_reply: {e}")
        await update.message.reply_text(f"❌ Có lỗi khi tạo: {e}")



def setup_bot(token: str) -> Application:
    """Setup và trả về Application instance"""
    # Xây dựng application và thêm một callback để set commands sau khi start
    async def post_init(application: Application) -> None:
        await application.bot.set_my_commands([
            ("start", "Hướng dẫn"),
            ("menu", "Menu riêng tư (Private)"),
            ("moi", "Tạo game mới"),
            ("lay_ve", "Lấy vé"),
            ("quay", "Quay số"),
            ("kinh", "Kiểm tra vé"),
            ("trang_thai", "Trạng thái"),
            ("ket_thuc", "Kết thúc game")
        ])

    application = Application.builder().token(token).post_init(post_init).build()
    
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
    application.add_handler(CallbackQueryHandler(lay_ve_callback, pattern="^lay_ve:"))
    application.add_handler(CallbackQueryHandler(generic_command_callback, pattern="^cmd:"))
    application.add_handler(MessageHandler(filters.REPLY & filters.TEXT & filters.ChatType.PRIVATE, handle_force_reply))
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

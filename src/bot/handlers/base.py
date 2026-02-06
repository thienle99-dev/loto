import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes
from config.config import WELCOME_MESSAGE, HELP_MESSAGE

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /start - hiển thị hướng dẫn tổng quan"""
    await update.message.reply_text(
        WELCOME_MESSAGE,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📜 Hướng dẫn", callback_data="cmd:tro_giup"),
             InlineKeyboardButton("📋 Menu", callback_data="cmd:menu_fallback")]
        ])
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /help"""
    await update.message.reply_text(
        HELP_MESSAGE,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Menu", callback_data="cmd:menu_fallback"),
             InlineKeyboardButton("🆕 Vòng mới", callback_data="cmd:vong_moi_input")]
        ])
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
            InlineKeyboardButton("🎲 Quay số", callback_data=f"cmd:quay{suffix}"),
            InlineKeyboardButton("🏆 Xếp hạng", callback_data=f"cmd:xep_hang{suffix}"),
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
    
    class MockMessage:
        def __init__(self, original_msg, target_id):
            self.chat = original_msg.chat
            self.chat_id = target_id
            self.from_user = original_msg.from_user
            self.text = f"/{command}"
            self.reply_to_message = original_msg.reply_to_message
            self.message_id = original_msg.message_id
        
        async def reply_text(self, *args, **kwargs):
            return await query.message.reply_text(*args, **kwargs)
        
        async def reply_photo(self, *args, **kwargs):
            return await query.message.reply_photo(*args, **kwargs)

    class ProxyUpdate:
        def __init__(self, original, message, chat):
            self.message = message
            self.effective_message = message
            self.effective_chat = chat
            self.effective_user = original.effective_user
            self.callback_query = original.callback_query
            self._effective_chat = chat
            self._effective_user = original.effective_user
            
    mock_message = MockMessage(query.message, target_chat_id)
    mock_chat = type('MockChat', (), {'id': target_chat_id, 'type': 'supergroup'})()
    mock_update = ProxyUpdate(update, mock_message, mock_chat)
    
    # Import handlers here to avoid circular dependencies
    from src.bot.handlers.game import vongmoi_command, endround_command, newsession_command, startsession_command, endsession_command
    from src.bot.handlers.player import layve_command, players_command
    from src.bot.handlers.spin import spin_command, reset_command, leaderboard_command, status_command, lastresult_command

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
        elif command == "menu_fallback":
            await menu_command(mock_update, context)
        elif command == "vong_moi_input":
            await query.message.reply_text(
                f"📝 *Tạo Vòng mới cho nhóm {target_chat_id}*\n\nHãy nhập tên vòng chơi mới của bạn:",
                parse_mode="Markdown",
                reply_markup=ForceReply(selective=True)
            )
            context.user_data["pending_action"] = "vong_moi"
            context.user_data["target_chat_id"] = target_chat_id
        elif command == "moi_input":
            await query.message.reply_text(
                f"📝 *Tạo Game mới cho nhóm {target_chat_id}*\n\nHãy nhập tên ván game mới:",
                parse_mode="Markdown",
                reply_markup=ForceReply(selective=True)
            )
            context.user_data["pending_action"] = "moi"
            context.user_data["target_chat_id"] = target_chat_id
        elif command == "ket_thuc_vong":
            await endround_command(mock_update, context)
        elif command == "ket_qua":
            await lastresult_command(mock_update, context)
        
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
    
    class ProxyUpdate:
        def __init__(self, original, chat_id):
            self.message = original.message
            self.effective_message = original.message
            self.effective_chat = type('MockChat', (), {'id': chat_id, 'type': 'supergroup'})()
            self.effective_user = original.effective_user
            self._effective_chat = self.effective_chat
            self._effective_user = original.effective_user
            
    mock_update = ProxyUpdate(update, target_chat_id)
    context.args = [text] 
    
    from src.bot.handlers.game import vongmoi_command, newsession_command

    try:
        if action == "vong_moi":
            await vongmoi_command(mock_update, context)
        elif action == "moi":
            await newsession_command(mock_update, context)
            
        del context.user_data["pending_action"]
        del context.user_data["target_chat_id"]
    except Exception as e:
        logger.error(f"Error in handle_force_reply: {e}")
        await update.message.reply_text(f"❌ Có lỗi khi tạo: {e}")

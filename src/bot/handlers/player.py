import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.constants import TICKET_CODES, TICKET_IMAGES
from src.bot.utils import escape_markdown, session_manager, ticket_display_name, ensure_active_session

logger = logging.getLogger(__name__)

async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /tham_gia - chuyển hướng sang lấy vé"""
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
        await update.message.reply_text("❌ Không có game nào đang chạy trong chat này.", parse_mode='Markdown')
        return

    if getattr(session, "started", False):
        await update.message.reply_text("⏱️ Game đã bắt đầu, không thể dùng `/tra_ve` để rời game nữa.", parse_mode='Markdown')
        return

    if getattr(session, "owner_id", None) == user_id:
        await update.message.reply_text("❌ Bạn là chủ phòng\\. Dùng `/ket_thuc` để kết thúc game thay vì `/tra_ve`.", parse_mode='Markdown')
        return

    user_tickets = getattr(session, "user_tickets", {})
    tickets = getattr(session, "tickets", {})
    code = user_tickets.pop(user_id, None)
    if code is not None and code in tickets:
        tickets.pop(code, None)
        session_manager.persist_session(chat_id)

    removed = session.remove_participant(user_id)
    if removed:
        session_manager.persist_session(chat_id)
    
    target_chat_id = chat_id
    suffix = f":{target_chat_id}"

    if removed or code is not None:
        await update.message.reply_text(
            "✅ Bạn đã trả vé và rời khỏi game hiện tại.", 
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎟️ Lấy vé mới", callback_data=f"cmd:lay_ve{suffix}")]])
        )
    else:
        await update.message.reply_text(
            "ℹ️ Bạn không nằm trong danh sách người chơi của game hiện tại.", 
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎟️ Lấy vé ngay", callback_data=f"cmd:lay_ve{suffix}")]])
        )

async def players_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /danh_sach - hiển thị danh sách người tham gia game"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)

    if not session:
        await update.message.reply_text("❌ *Chưa có game nào đang chạy trong chat này\\!*", parse_mode='Markdown')
        return

    participants = session.get_participants()
    owner_id = getattr(session, "owner_id", None)
    game_name = getattr(session, "game_name", None)

    if not participants and owner_id is None:
        await update.message.reply_text("ℹ️ Hiện chưa có ai lấy vé / tham gia game.", parse_mode='Markdown')
        return

    lines = []
    owner_line_done = False
    user_tickets = getattr(session, "user_tickets", {})
    for p in participants:
        uid = p.get("user_id")
        name = p.get("name") or str(uid)
        prefix = "-"
        suffix = ""
        
        # Lấy thông tin vé
        ticket_code = user_tickets.get(uid)
        ticket_info = f" ({escape_markdown(ticket_display_name(ticket_code))})" if ticket_code else " (Chưa lấy vé)"
        
        if owner_id is not None and uid == owner_id and not owner_line_done:
            prefix = "⭐"
            suffix = " *(Host)*"
            owner_line_done = True
        
        lines.append(f"{prefix} {escape_markdown(name)}{suffix}{ticket_info}")

    if owner_id is not None and not owner_line_done:
        lines.insert(0, "⭐ Chủ phòng (Host)")

    header = "👥 *Danh sách người đã lấy vé (tham gia game):*\n\n"
    if game_name:
        header += f"🕹️ Game: `{escape_markdown(game_name)}`\n"
    header += f"📊 Tổng: `{len(lines)}` người\n\n"

    target_chat_id = chat_id
    suffix = f":{target_chat_id}"

    await update.message.reply_text(
        header + "\n".join(lines), 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎟️ Lấy vé", callback_data=f"cmd:lay_ve{suffix}"),
             InlineKeyboardButton("🚀 Bắt đầu Game", callback_data=f"cmd:bat_dau{suffix}")]
        ])
    )

async def layve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /lay_ve"""
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

    if not await ensure_active_session(update, chat_id, session):
        return

    if not hasattr(session, "tickets"): session.tickets = {}
    if not hasattr(session, "user_tickets"): session.user_tickets = {}

    tickets = session.tickets
    user_tickets = session.user_tickets

    if getattr(session, "started", False):
        current = user_tickets.get(user_id)
        msg = f"ℹ️ Game đã bắt đầu\\. Vé của bạn là: {escape_markdown(ticket_display_name(current))}\\. Không thể đổi vé nữa." if current else \
              "ℹ️ Game đã bắt đầu và bạn chưa đăng ký vé nào\\. Không thể lấy vé mới nữa."
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    is_remote = (update.effective_chat.type == "private")
    target_chat_id = chat_id

    if not context.args:
        lines = []
        current = user_tickets.get(user_id)
        suffix = f":{target_chat_id}" if is_remote else ""
        
        for code in TICKET_CODES:
            holder_id = tickets.get(code)
            status = "🟢 *Còn trống*" if holder_id is None else \
                     "🧾 *Bạn đang giữ*" if holder_id == user_id else \
                     "🔴 *Đã có người lấy*"
            lines.append(f"- {escape_markdown(ticket_display_name(code))} → {status}")

        header = "🎟️ *Danh sách vé hiện có:*\n\n"
        if current:
            header += f"🧾 Vé hiện tại của bạn: {escape_markdown(ticket_display_name(current))}\n\n"
        else:
            header += "🧾 Bạn chưa chọn vé nào\\.\n\n"
        
        participants = getattr(session, "get_participants", lambda: [])()
        name_by_id = {p.get("user_id"): p.get("name") or str(p.get("user_id")) for p in participants if p.get("user_id") is not None}

        people_lines = [f"- {escape_markdown(name_by_id.get(uid, str(uid)))}: {escape_markdown(ticket_display_name(code))}" 
                        for uid, code in user_tickets.items()]

        if people_lines:
            header += "👥 *Danh sách người đã lấy vé:*\n" + "\n".join(people_lines) + "\n\n"

        header += "Chọn vé bên dưới hoặc gõ `/lay_ve <mã_vé>`\\. Ví dụ: `/lay_ve tim1`"
        keyboard = []
        row = []
        for i, code in enumerate(TICKET_CODES):
            holder_id = tickets.get(code)
            display = ticket_display_name(code)
            label = f"✅ {display}" if holder_id == user_id else \
                    f"🔴 {display}" if holder_id else display
            row.append(InlineKeyboardButton(label, callback_data=f"lay_ve:{code}{suffix}"))
            if len(row) == 4 or i == len(TICKET_CODES) - 1:
                keyboard.append(row)
                row = []
        
        await update.message.reply_text(header + "\n" + "\n".join(lines), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    code = context.args[0].lower()
    if code not in TICKET_CODES:
        valid_list = ", ".join(f"{escape_markdown(ticket_display_name(c))} (`{c}`)" for c in TICKET_CODES)
        await update.message.reply_text(f"❌ *Mã vé không hợp lệ\\!*\n\nCác vé hợp lệ: {valid_list}", parse_mode="Markdown")
        return

    holder_id = tickets.get(code)
    current = user_tickets.get(user_id)

    if holder_id is not None and holder_id != user_id:
        await update.message.reply_text(f"⚠️ Vé {escape_markdown(ticket_display_name(code))} đã có người chọn rồi.", parse_mode="Markdown")
        return

    if current and current != code:
        tickets.pop(current, None)

    tickets[code] = user_id
    user_tickets[user_id] = code
    session.add_participant(user_id=user_id, name=user.full_name or (user.username or str(user_id)))
    session_manager.persist_session(chat_id)

    people_lines = [f"- {escape_markdown(str(uid))}: {escape_markdown(ticket_display_name(c))}" for uid, c in user_tickets.items()]
    list_text = "\n\n👥 *Danh sách người đã lấy vé:*\n" + "\n".join(people_lines) if people_lines else ""

    await update.message.reply_text(
        f"✅ Bạn đã lấy vé: {escape_markdown(ticket_display_name(code))} và tham gia game." + list_text,
        parse_mode="Markdown"
    )

    image_path = TICKET_IMAGES.get(code)
    if image_path and image_path.is_file():
        try:
            with open(image_path, "rb") as f:
                await update.message.reply_photo(photo=f, caption=f"🎟️ Vé của bạn: {escape_markdown(ticket_display_name(code))}", parse_mode="Markdown")
        except Exception as e:
            logger.error("Không thể gửi ảnh vé %s: %s", code, e)

async def lay_ve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi người dùng chọn vé qua menu nút bấm"""
    query = update.callback_query
    data_parts = query.data.split(":")
    try:
        code = data_parts[1]
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

    if not hasattr(session, "tickets"): session.tickets = {}
    if not hasattr(session, "user_tickets"): session.user_tickets = {}

    tickets = session.tickets
    user_tickets = session.user_tickets

    if getattr(session, "started", False):
        await query.answer("⏱️ Game đã bắt đầu, không thể lấy/đổi vé nữa.", show_alert=True)
        return

    holder_id = tickets.get(code)
    current = user_tickets.get(user_id)

    if holder_id is not None and holder_id != user_id:
        await query.answer(f"⚠️ Vé {ticket_display_name(code)} đã có người chọn rồi.", show_alert=True)
        return
        
    if holder_id == user_id:
        await query.answer(f"🧾 Bạn đang giữ vé {ticket_display_name(code)} rồi.")
        return

    if current and current != code:
        tickets.pop(current, None)

    tickets[code] = user_id
    user_tickets[user_id] = code
    session.add_participant(user_id=user_id, name=user.full_name or (user.username or str(user_id)))
    session_manager.persist_session(chat_id)

    await query.answer(f"✅ Đã chọn {ticket_display_name(code)}!")
    await query.message.reply_text(f"✅ {escape_markdown(user.full_name)} đã lấy vé: {escape_markdown(ticket_display_name(code))}", parse_mode="Markdown")

    image_path = TICKET_IMAGES.get(code)
    if image_path and image_path.is_file():
        try:
            with open(image_path, "rb") as f:
                await query.message.reply_photo(photo=f, caption=f"🎟️ Vé của: {escape_markdown(user.full_name)} - {escape_markdown(ticket_display_name(code))}", parse_mode="Markdown")
        except Exception as e:
            logger.error("Không thể gửi ảnh vé %s: %s", code, e)

    # Cập nhật menu nút bấm
    keyboard = []
    row = []
    suffix = f":{chat_id}" if chat_id != query.message.chat_id else ""
    for i, c in enumerate(TICKET_CODES):
        h_id = tickets.get(c)
        display = ticket_display_name(c)
        label = f"✅ {display}" if h_id == user_id else f"🔴 {display}" if h_id else display
        row.append(InlineKeyboardButton(label, callback_data=f"lay_ve:{c}{suffix}"))
        if len(row) == 4 or i == len(TICKET_CODES) - 1:
            keyboard.append(row)
            row = []
    
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

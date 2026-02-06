from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.constants import active_rounds, MAX_NUMBERS, DEFAULT_REMOVE_AFTER_SPIN, last_results
from src.bot.utils import escape_markdown, session_manager, get_chat_stats
from src.utils.validators import validate_range, validate_number
from src.db.sqlite_store import save_stats, save_last_result

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
    
    target_chat_id = chat_id
    suffix = f":{target_chat_id}"

    await update.message.reply_text(
        f"🛑 Đã kết thúc vòng chơi *{escape_markdown(round_name)}*\\.\n\n"
        "Giờ bạn có thể tạo vòng mới hoặc ván game mới.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Vòng mới", callback_data=f"cmd:vong_moi_input{suffix}"),
             InlineKeyboardButton("🕹️ Game mới", callback_data=f"cmd:moi_input{suffix}")]
        ])
    )

async def newsession_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /moi <tên_game>"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id

    if chat_id not in active_rounds:
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"
        await update.message.reply_text(
            "⚠️ *Bạn cần tạo vòng chơi trước khi tạo game\\!*\n\n"
            "Việc tạo vòng giúp bot thống kê điểm và lưu lịch sử chính xác hơn.\n"
            "Hãy dùng nút bên dưới hoặc gõ `/vong_moi <tên_vòng>`.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Tạo Vòng mới", callback_data=f"cmd:vong_moi_input{suffix}")]
            ])
        )
        return

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
        session = session_manager.create_session(
            chat_id,
            1,
            MAX_NUMBERS,
            DEFAULT_REMOVE_AFTER_SPIN
        )
        session.game_name = game_name
        session.owner_id = user_id

        round_info = active_rounds.get(chat_id)
        if round_info:
            session.round_name = round_info.get("round_name")

        session.add_participant(user_id=user_id, name=user.full_name or (user.username or str(user_id)))
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
    
    if chat_id not in active_rounds:
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"
        await update.message.reply_text(
            "⚠️ *Bạn cần tạo vòng chơi trước khi tạo game\\!*\n\n"
            "Hãy dùng nút bên dưới hoặc gõ `/vong_moi <tên_vòng>`.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Tạo Vòng mới", callback_data=f"cmd:vong_moi_input{suffix}")]
            ])
        )
        return

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
    
    start_arg = context.args[0]
    end_arg = context.args[1]
    
    is_valid_start, start_num, error_start = validate_number(start_arg)
    is_valid_end, end_num, error_end = validate_number(end_arg)
    
    if not is_valid_start:
        await update.message.reply_text(f"❌ Lỗi: {error_start}")
        return
    if not is_valid_end:
        await update.message.reply_text(f"❌ Lỗi: {error_end}")
        return
    
    is_valid, error_msg = validate_range(start_num, end_num)
    if not is_valid:
        await update.message.reply_text(f"❌ Lỗi: {error_msg}")
        return
    
    try:
        session = session_manager.create_session(
            chat_id,
            start_num,
            end_num,
            DEFAULT_REMOVE_AFTER_SPIN
        )
        session.owner_id = user_id

        round_info = active_rounds.get(chat_id)
        if round_info:
            session.round_name = round_info.get("round_name")

        session.add_participant(user_id=user_id, name=user.full_name or (user.username or str(user_id)))
        session_manager.persist_session(chat_id)
        
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"

        await update.message.reply_text(
            f"✅ *Đã tạo game mới\\!*\n\n"
            f"📊 Khoảng số: `{start_num} -> {end_num}`\n"
            f"📊 Tổng số: `{session.get_total_numbers()}`\n"
            f"⚙️ Loại bỏ sau khi quay: `{'Có' if session.remove_after_spin else 'Không'}`\n\n"
            f"Người chơi chọn vé bằng nút bên dưới hoặc `/lay_ve`\\.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎟️ Lấy vé", callback_data=f"cmd:lay_ve{suffix}"), 
                 InlineKeyboardButton("👥 Danh sách", callback_data=f"cmd:danh_sach{suffix}")],
                [InlineKeyboardButton("🚀 Bắt đầu Game", callback_data=f"cmd:bat_dau{suffix}")]
            ])
        )
    except ValueError as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")

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

async def endsession_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /ket_thuc"""
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

    owner_id = getattr(session, "owner_id", user_id)
    if owner_id != user_id:
        await update.message.reply_text(
            "❌ Chỉ *host* (người tạo game) mới được quyền kết thúc game với `/ket_thuc`.",
            parse_mode='Markdown'
        )
        return

    game_name = getattr(session, "game_name", None)
    chat_stats = get_chat_stats(chat_id)

    participations = chat_stats["participations"]
    for p in session.get_participants():
        uid = p.get("user_id")
        if uid is None: continue
        name = p.get("name") or str(uid)
        info = participations.get(uid, {"count": 0.0, "name": name})
        info["count"] += 1.0
        info["name"] = name
        participations[uid] = info

    wins = chat_stats["wins"]
    unique_winners = {w.get("user_id"): w.get("name") or str(w.get("user_id")) 
                      for w in getattr(session, "winners", []) if w.get("user_id") is not None}

    if unique_winners:
        share = 1.0 / len(unique_winners)
        for uid, name in unique_winners.items():
            info = wins.get(uid, {"count": 0.0, "name": name})
            info["count"] += share
            info["name"] = name
            wins[uid] = info

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
    save_stats(chat_id, chat_stats)
    save_last_result(chat_id, result_data)
    session_manager.delete_session(chat_id)

    target_chat_id = chat_id
    suffix = f":{target_chat_id}"
    
    msg = f"🛑 *Đã kết thúc ván chơi* `{escape_markdown(game_name)}`\\.\n\n" if game_name else \
          "🛑 *Đã kết thúc game hiện tại\\!* \n\n"
    msg += "Bạn có thể tạo ván chơi mới hoặc vòng mới bằng nút bên dưới\\."

    await update.message.reply_text(
        msg, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Vòng mới", callback_data=f"cmd:vong_moi_input{suffix}"),
             InlineKeyboardButton("🕹️ Game mới", callback_data=f"cmd:moi_input{suffix}")]
        ])
    )

async def toggle_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /toggle_remove"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)
    
    if not session:
        await update.message.reply_text(
            "❌ *Chưa có game nào trong chat\\!*\n\n"
            "Host dùng `/moi <tên_game>` hoặc `/pham_vi <x> <y>` để tạo game trước nhé\\.",
            parse_mode='Markdown'
        )
        return
    
    from src.bot.wheel import set_remove_mode
    # Toggle remove mode
    new_mode = not session.remove_after_spin
    set_remove_mode(session, new_mode)
    
    # Lưu cấu hình session
    session_manager.persist_session(chat_id)

    target_chat_id = chat_id
    suffix = f":{target_chat_id}"

    mode_text = "Có" if new_mode else "Không"
    await update.message.reply_text(
        f"⚙️ *Chế độ loại bỏ:* `{mode_text}`\n\n"
        f"{'✅ Số đã quay sẽ bị loại bỏ' if new_mode else '✅ Số đã quay vẫn có thể xuất hiện lại'}",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Quay số", callback_data=f"cmd:quay{suffix}"),
             InlineKeyboardButton("📋 Menu", callback_data=f"cmd:menu_fallback{suffix}")]
        ])
    )

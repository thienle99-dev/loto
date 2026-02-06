from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.constants import active_rounds, round_history, MAX_NUMBERS, DEFAULT_REMOVE_AFTER_SPIN, last_results, BET_AMOUNT
from src.bot.utils import escape_markdown, session_manager, get_chat_stats
from src.utils.validators import validate_range, validate_number
from src.db.sqlite_store import save_stats, save_last_result, save_active_round, delete_active_round_row

async def vongmoi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /vong_moi <tên_vòng> - tạo vòng chơi mới trong chat."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id

    if not context.args:
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"
        await update.message.reply_text(
            "❌ *Sai cú pháp\\!*\n\n"
            "Sử dụng: `/vong_moi <tên_vòng>`\n"
            "Ví dụ: `/vong_moi Loto tối nay`\n\n"
            "ℹ️ Vòng chơi là đơn vị lớn nhất, chứa nhiều ván game bên trong.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Menu điều khiển", callback_data=f"cmd:menu_fallback{suffix}")]])
        )
        return

    round_name = " ".join(context.args).strip()
    if not round_name:
        await update.message.reply_text(
            "❌ Tên vòng không được để trống.",
            parse_mode="Markdown",
        )
        return

    # Kiểm tra nếu đang có ván game đang chạy
    if session_manager.has_session(chat_id):
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"
        await update.message.reply_text(
            "⚠️ *Đang có ván game hoạt động\\!*\n\n"
            "Vui lòng kết thúc ván game hiện tại trước khi tạo vòng chơi mới bì vòng mới sẽ làm thay đổi lịch sử thống kê.\n"
            "Hãy dùng các nút bên dưới để điều khiển nhanh.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎲 Quay số", callback_data=f"cmd:quay{suffix}"),
                 InlineKeyboardButton("🛑 Kết thúc Game", callback_data=f"cmd:ket_thuc{suffix}")]
            ])
        )
        return

    # Kiểm tra nếu đã có vòng đang hoạt động
    if chat_id in active_rounds:
        current_round = active_rounds[chat_id].get("round_name", "Không tên")
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"
        await update.message.reply_text(
            f"⚠️ *Đang có vòng chơi hoạt động\\!*\n\n"
            f"Vòng: `{escape_markdown(current_round)}`\n"
            f"Vui lòng kết thúc vòng cũ trước khi tạo vòng mới\\.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏁 Kết thúc Vòng cũ", callback_data=f"cmd:ket_thuc_vong{suffix}")]
            ])
        )
        return

    # Lưu vào RAM và DB
    active_rounds[chat_id] = {
        "round_name": round_name,
        "owner_id": user_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_active_round(chat_id, active_rounds[chat_id])
    
    # Khởi tạo lịch sử game cho vòng mới
    round_history[chat_id] = []
    
    # Reset thống kê của chat cho vòng mới (để token tính từ 0)
    chat_stats = get_chat_stats(chat_id)
    chat_stats["wins"] = {}
    chat_stats["participations"] = {}
    save_stats(chat_id, chat_stats)

    target_chat_id = chat_id
    suffix = f":{target_chat_id}"

    await update.message.reply_text(
        f"✅ *Đã tạo vòng chơi mới\\!* \n"
        f"🔄 Tên vòng: `{escape_markdown(round_name)}`\n"
        f"🧹 *Đã reset toàn bộ Token & Thống kê về 0.*\n\n"
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
    owner_id = round_info.get("owner_id")
    user_id = update.effective_user.id

    # Bỏ qua kiểm tra quyền sở hữu theo yêu cầu

    # 2. Kiểm tra nếu đang có ván game đang chạy trong vòng này
    if session_manager.has_session(chat_id):
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"
        await update.message.reply_text(
            "⚠️ *Không thể kết thúc vòng khi còn ván game đang chạy\\!*\n\n"
            "Vui lòng kết thúc ván game bằng `/ket_thuc` trước.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎲 Quay số", callback_data=f"cmd:quay{suffix}"),
                 InlineKeyboardButton("🛑 Kết thúc Game", callback_data=f"cmd:ket_thuc{suffix}")]
            ])
        )
        return

    # Hiển thị BXH cuối cùng của vòng trước khi xoá
    games = round_history.get(chat_id, [])
    if games:
        from src.bot.utils import calculate_round_tokens, get_round_leaderboard_text
        user_tokens = calculate_round_tokens(games)
        leaderboard_msg = get_round_leaderboard_text(round_name, user_tokens)
        await update.message.reply_text(
            f"🏁 *KẾT THÚC VÒNG CHƠI: {escape_markdown(round_name)}*\n\n" + leaderboard_msg,
            parse_mode='Markdown'
        )

    # 3. Xoá vòng chơi khỏi active_rounds (RAM) và DB
    del active_rounds[chat_id]
    delete_active_round_row(chat_id)
    
    # Xóa lịch sử game của vòng
    if chat_id in round_history:
        del round_history[chat_id]
    
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
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"
        await update.message.reply_text(
            "⚠️ *Chat này đang có game hoạt động\\!*\n\n"
            "Bạn có thể dùng bảng điều khiển bên dưới để tiếp tục hoặc kết thúc game cũ trước khi tạo game mới\\.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Menu điều khiển", callback_data=f"cmd:menu_fallback{suffix}")],
                [InlineKeyboardButton("🎲 Quay số", callback_data=f"cmd:quay{suffix}"),
                 InlineKeyboardButton("🛑 Kết thúc Game", callback_data=f"cmd:ket_thuc{suffix}")]
            ])
        )
        return

    if not context.args:
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"
        await update.message.reply_text(
            "❌ *Sai cú pháp\\!*\n\n"
            "Sử dụng: `/moi <tên_game>`\n"
            "Ví dụ: `/moi Loto tối nay`\n\n"
            "ℹ️ Ván game này sẽ thuộc vòng chơi hiện tại.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Menu điều khiển", callback_data=f"cmd:menu_fallback{suffix}")]])
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

        round_name = session.round_name if hasattr(session, 'round_name') else "Không có"

        await update.message.reply_text(
            f"✅ *Đã tạo game mới\\!*\n\n"
            f"🔄 Vòng: `{escape_markdown(round_name)}`\n"
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
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"
        await update.message.reply_text(
            "⚠️ *Chat này đang có game hoạt động\\!*\n\n"
            "Bạn có thể dùng bảng điều khiển bên dưới để tiếp tục hoặc kết thúc game cũ trước khi tạo game mới\\.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Menu điều khiển", callback_data=f"cmd:menu_fallback{suffix}")],
                [InlineKeyboardButton("🎲 Quay số", callback_data=f"cmd:quay{suffix}"),
                 InlineKeyboardButton("🛑 Kết thúc Game", callback_data=f"cmd:ket_thuc{suffix}")]
            ])
        )
        return

    if not context.args or len(context.args) < 2:
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"
        await update.message.reply_text(
            "❌ *Sai cú pháp\\!*\n\n"
            "Sử dụng: `/pham_vi <x> <y>`\n"
            "Ví dụ: `/pham_vi 1 100`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Menu điều khiển", callback_data=f"cmd:menu_fallback{suffix}")]])
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

        round_name = session.round_name if hasattr(session, 'round_name') else "Không có"

        await update.message.reply_text(
            f"✅ *Đã tạo game mới\\!*\n\n"
            f"🔄 Vòng: `{escape_markdown(round_name)}`\n"
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
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"
        await update.message.reply_text(
            "❌ Chỉ *host* (người tạo game) mới được quyền bắt đầu game bằng `/bat_dau`.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎟️ Lấy vé", callback_data=f"cmd:lay_ve{suffix}"),
                 InlineKeyboardButton("👥 Danh sách", callback_data=f"cmd:danh_sach{suffix}")]
            ])
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

    target_chat_id = chat_id
    suffix = f":{target_chat_id}"

    sent_msg = await update.message.reply_text(
        text, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Quay số đầu tiên", callback_data=f"cmd:quay{suffix}")]
        ])
    )
    session.last_control_message_id = sent_msg.message_id
    session_manager.persist_session(chat_id)

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
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"
        await update.message.reply_text(
            "❌ Chỉ *host* (người tạo game) mới được quyền kết thúc game với `/ket_thuc`.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎲 Quay số", callback_data=f"cmd:quay{suffix}"),
                 InlineKeyboardButton("📊 Trạng thái", callback_data=f"cmd:trang_thai{suffix}")]
            ])
        )
        return

    game_name = getattr(session, "game_name", None)
    chat_stats = get_chat_stats(chat_id)

    # Đếm số lần tham gia
    participations = chat_stats["participations"]
    participants = session.get_participants()
    total_players = len(participants)
    
    for p in participants:
        uid = p.get("user_id")
        if uid is None: continue
        name = p.get("name") or str(uid)
        info = participations.get(uid, {"count": 0.0, "name": name})
        info["count"] += 1.0
        info["name"] = name
        participations[uid] = info

    # Tính điểm token theo công thức mới: CHỈ TÍNH KHI CÓ NGƯỜI THẮNG
    wins = chat_stats["wins"]
    unique_winners = {w.get("user_id"): w.get("name") or str(w.get("user_id")) 
                      for w in getattr(session, "winners", []) if w.get("user_id") is not None}

    token_per_winner = 0
    bet_amount = BET_AMOUNT

    if total_players > 0 and unique_winners:
        num_winners = len(unique_winners)
        # Người thắng: nhận phần tiền của người thua
        # Công thức zero-sum: (Tổng người chơi * cược / Số người thắng) - cược
        token_per_winner = (total_players * bet_amount / num_winners) - bet_amount
        
        for uid, name in unique_winners.items():
            info = wins.get(uid, {"count": 0.0, "name": name})
            info["count"] += token_per_winner
            info["name"] = name
            wins[uid] = info
        
        # Người thua: mất cược
        loser_ids = [p.get("user_id") for p in participants 
                     if p.get("user_id") is not None and p.get("user_id") not in unique_winners]
        
        for uid in loser_ids:
            p_info = next((p for p in participants if p.get("user_id") == uid), None)
            name = p_info.get("name") if p_info else str(uid)
            info = wins.get(uid, {"count": 0.0, "name": name})
            info["count"] -= bet_amount
            info["name"] = name
            wins[uid] = info

    # Xây dựng danh sách biến động token ván này
    token_results = []
    if total_players > 0 and unique_winners:
        actual_participants_list = session.get_participants()
        for p in actual_participants_list:
            p_uid = p.get("user_id")
            if p_uid is None: continue
            p_name = p.get("name") or str(p_uid)
            
            if p_uid in unique_winners:
                token_results.append(f"   • {escape_markdown(p_name)}: `+{token_per_winner:.1f}` 🏆")
            else:
                token_results.append(f"   • {escape_markdown(p_name)}: `-{bet_amount:.1f}`")
    elif total_players > 0 and not unique_winners:
        token_results.append("   _(Không ai thắng, token không thay đổi)_")
    
    token_changes_msg = ""
    if token_results:
        token_changes_msg = "\n\n💰 *Biến động Token ván này:*\n" + "\n".join(token_results)
        
    # Tính toán Token tổng cộng trong vòng (cumulative)
    cumulative_results = []
    # Sắp xếp theo token giảm dần
    sorted_wins = sorted(wins.items(), key=lambda x: x[1].get("count", 0.0), reverse=True)
    for uid, info in sorted_wins:
        total_token = info.get("count", 0.0)
        p_name = info.get("name") or str(uid)
        txt_token = f"+{total_token:.1f}" if total_token > 0 else f"{total_token:.1f}"
        cumulative_results.append(f"   • {escape_markdown(p_name)}: `{txt_token}`")
        
    if cumulative_results:
        token_changes_msg += "\n\n🏆 *Tổng Token sau ván này:*\n" + "\n".join(cumulative_results)

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
    
    # Lưu game vào lịch sử vòng chơi
    if chat_id in active_rounds:
        if chat_id not in round_history:
            round_history[chat_id] = []
        
        # Chỉ tính những người thực sự có vé là người tham gia ván này
        ticket_holders = set()
        if hasattr(session, 'user_tickets'):
            # Convert keys to int for safety
            ticket_holders = {int(uid) for uid in session.user_tickets.keys()}
        
        all_participants = session.get_participants()
        actual_participants = [p for p in all_participants if int(p.get("user_id")) in ticket_holders]
        
        # Nếu host cũng chơi (có vé) thì đã nằm trong actual_participants. 
        # Nếu host không chơi nhưng bạn vẫn muốn họ có trong list stats (với 0 điểm) 
        # thì logic tính toán ở leaderboard sẽ tự lo. Ở đây ta chỉ lấy người có vé.

        game_record = {
            "game_name": game_name,
            "host_name": host_name,
            "winners": list(getattr(session, "winners", [])),
            "participants": actual_participants,
            "numbers_drawn": len(session.history),
            "ended_at": datetime.now().isoformat(timespec="seconds"),
        }
        round_history[chat_id].append(game_record)
    
    session_manager.delete_session(chat_id)

    target_chat_id = chat_id
    suffix = f":{target_chat_id}"
    
    msg = f"🛑 *Đã kết thúc ván chơi* `{escape_markdown(game_name)}`\\.\n\n" if game_name else \
          "🛑 *Đã kết thúc game hiện tại\\!* \n\n"
    msg += "Bạn có thể tạo ván chơi mới hoặc vòng mới bằng nút bên dưới\\."
    msg += token_changes_msg

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

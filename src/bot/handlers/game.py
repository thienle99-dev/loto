from datetime import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.constants import MAX_NUMBERS, DEFAULT_REMOVE_AFTER_SPIN, last_results, BET_AMOUNT, COOLDOWN_CHECK_SECONDS
from src.bot.utils import escape_markdown, session_manager, get_chat_stats, ensure_active_session
from src.utils.validators import validate_range, validate_number
from src.db.sqlite_store import save_stats, save_last_result
from src.bot.worker import queued_handler

logger = logging.getLogger(__name__)

# Cache thời gian kiểm tra kinh của từng user: {(chat_id, user_id): datetime}
last_check_time: dict[tuple[int, int], datetime] = {}

@queued_handler
async def cuoc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /cuoc <số_tiền>"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    session = await session_manager.get_session(chat_id)
    if not session:
        await update.message.reply_text("❌ *Chưa có game nào!* Hãy dùng `/moi` trước.", parse_mode='Markdown')
        return

    if session.owner_id != user.id:
        await update.message.reply_text("⚠️ Chỉ Host mới có quyền thay đổi tiền cược.")
        return

    if session.started:
        await update.message.reply_text("⚠️ Game đã bắt đầu, không thể đổi tiền cược.")
        return

    if not context.args:
        await update.message.reply_text(f"💰 Tiền cược hiện tại: `{session.bet_amount:.1f}`\nSử dụng: `/cuoc <số_tiền>` để thay đổi.", parse_mode='Markdown')
        return

    try:
        amount = float(context.args[0])
        if amount < 0:
            await update.message.reply_text("❌ Tiền cược không được âm.")
            return
        
        session.bet_amount = amount
        await session_manager.persist_session(chat_id)
        await update.message.reply_text(f"✅ Đã đặt tiền cược cho ván này là: `{amount:.1f}` token.", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ Vui lòng nhập một số hợp lệ.")

async def newsession_command_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Logic xử lý lệnh /moi <tên_game>"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id

    if await session_manager.has_session(chat_id):
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
        session = await session_manager.create_session(
            chat_id,
            1,
            MAX_NUMBERS,
            DEFAULT_REMOVE_AFTER_SPIN,
            BET_AMOUNT
        )
        session.game_name = game_name
        session.owner_id = user_id

        session.add_participant(user_id=user_id, name=user.full_name or (user.username or str(user_id)))
        await session_manager.persist_session(chat_id)

        target_chat_id = chat_id
        suffix = f":{target_chat_id}"

        round_name = session.round_name if hasattr(session, 'round_name') else "Không có"

        await update.message.reply_text(
            f"✅ *Đã tạo game mới\\!*\n\n"
            f"🕹️ Tên game: `{escape_markdown(game_name)}`\n"
            f"� Tiền cược: `{session.bet_amount:.1f}`\n"
            f"�📊 Khoảng số: `1 -> {MAX_NUMBERS}`\n"
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

@queued_handler
async def newsession_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /moi <tên_game>"""
    await newsession_command_logic(update, context)

async def setrange_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /pham_vi <x> <y>"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    
    if await session_manager.has_session(chat_id):
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
        session = await session_manager.create_session(
            chat_id,
            start_num,
            end_num,
            DEFAULT_REMOVE_AFTER_SPIN
        )
        session.owner_id = user_id

        session.owner_id = user_id

        session.add_participant(user_id=user_id, name=user.full_name or (user.username or str(user_id)))
        await session_manager.persist_session(chat_id)
        
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"

        round_name = session.round_name if hasattr(session, 'round_name') else "Không có"

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

async def startsession_command_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Logic xử lý lệnh /bat_dau"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    session = await session_manager.get_session(chat_id)

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
    await session_manager.persist_session(chat_id)

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
    await session_manager.persist_session(chat_id)

@queued_handler
async def startsession_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /bat_dau - host bấm để bắt đầu game"""
    await startsession_command_logic(update, context)

async def endsession_command_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Logic xử lý lệnh /ket_thuc"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    session = await session_manager.get_session(chat_id)

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
    chat_stats = await get_chat_stats(chat_id)

    # Đếm số lần tham gia - CHỈ TÍNH NGƯỜI CÓ VÉ
    participations = chat_stats["participations"]
    
    # Lấy danh sách người có vé (người chơi thực sự)
    user_tickets = getattr(session, "user_tickets", {})
    ticket_holder_ids = set(user_tickets.keys())
    
    # Lọc participants chỉ lấy người có vé
    all_participants = session.get_participants()
    actual_players = [p for p in all_participants if p.get("user_id") in ticket_holder_ids]
    total_players = len(actual_players)
    
    for p in actual_players:
        uid = p.get("user_id")
        if uid is None: continue
        name = p.get("name") or str(uid)
        username = p.get("username")
        info = participations.get(uid, {"count": 0.0, "name": name, "username": username})
        info["count"] += 1.0
        info["name"] = name
        info["username"] = username
        participations[uid] = info

    # Tính điểm token theo công thức mới: CHỈ TÍNH KHI CÓ NGƯỜI THẮNG
    wins = chat_stats["wins"]
    # Lấy danh sách winner (CHỈ TÍNH NGƯỜI CÓ TRONG DANH SÁCH actual_players)
    unique_winners = {w.get("user_id"): (w.get("name") or str(w.get("user_id")), w.get("username")) 
                      for w in getattr(session, "winners", []) 
                      if w.get("user_id") is not None and w.get("user_id") in ticket_holder_ids}

    token_per_winner = 0
    bet_amount = getattr(session, "bet_amount", BET_AMOUNT)

    if total_players > 0 and unique_winners:
        num_winners = len(unique_winners)
        # Người thắng: nhận phần tiền của người thua
        # Công thức zero-sum: (Tổng người chơi * cược / Số người thắng) - cược
        token_per_winner = (total_players * bet_amount / num_winners) - bet_amount
        
        split_msg = ""
        if num_winners > 1:
            split_msg = f"\n💡 *Chia đều thưởng:* Mỗi người trúng nhận `+{token_per_winner:.1f}` token từ {total_players - num_winners} người thua."

        for uid, (name, username) in unique_winners.items():
            info = wins.get(uid, {"count": 0.0, "name": name, "username": username})
            info["count"] += token_per_winner
            info["name"] = name
            info["username"] = username
            wins[uid] = info
        
        # Người thua: mất cược (CHỈ TÍNH NGƯỜI CÓ VÉ)
        loser_ids = [p.get("user_id") for p in actual_players 
                     if p.get("user_id") is not None and p.get("user_id") not in unique_winners]
        
        for uid in loser_ids:
            p_info = next((p for p in actual_players if p.get("user_id") == uid), None)
            name = p_info.get("name") if p_info else str(uid)
            username = p_info.get("username") if p_info else None
            info = wins.get(uid, {"count": 0.0, "name": name, "username": username})
            info["count"] -= bet_amount
            info["name"] = name
            info["username"] = username
            wins[uid] = info

    # Xây dựng danh sách biến động token ván này

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
    
    await session_manager.delete_session(chat_id)

    target_chat_id = chat_id
    suffix = f":{target_chat_id}"
    
    msg = f"🛑 *Đã kết thúc ván chơi* `{escape_markdown(game_name)}`\\.\n\n" if game_name else \
          "🛑 *Đã kết thúc game hiện tại\\!* \n\n"
    msg += "Bạn có thể tạo ván chơi mới hoặc vòng mới bằng nút bên dưới\\."

    await update.message.reply_text(
        msg + token_changes_msg, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🕹️ Game mới", callback_data=f"cmd:moi_input{suffix}")]
        ])
    )

@queued_handler
async def endsession_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /ket_thuc"""
    await endsession_command_logic(update, context)

async def check_command_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Logic xử lý lệnh /kinh"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    session = await session_manager.get_session(chat_id)

    key = (chat_id, user.id)
    now = datetime.now()
    if last_check_time.get(key) and (now - last_check_time[key]).total_seconds() < COOLDOWN_CHECK_SECONDS:
        await update.message.reply_text("⏱️ Đợi vài giây rồi thử lại nhé.", parse_mode='Markdown')
        return

    if not session:
        await update.message.reply_text("❌ *Chưa có game nào!*", parse_mode='Markdown')
        return

    if not await ensure_active_session(update, chat_id, session):
        return

    if not getattr(session, "started", False):
        await update.message.reply_text("⏱️ *Game chưa bắt đầu!*", parse_mode='Markdown')
        return

    user_tickets = getattr(session, "user_tickets", {})
    if user.id not in user_tickets:
        await update.message.reply_text("🎟️ *Bạn cần lấy vé trước khi chơi!*", parse_mode='Markdown')
        return

    if not context.args:
        await update.message.reply_text("❌ *Sai cú pháp!* /kinh <danh_sách_số>", parse_mode='Markdown')
        return

    raw_text = " ".join(context.args)
    for ch in [",", ";", "|"]: raw_text = raw_text.replace(ch, " ")
    tokens = [t for t in raw_text.split() if t.strip()]

    drawn_numbers = {item.get("number") for item in session.history}
    remaining_numbers = set(session.available_numbers)

    matched, not_drawn, invalid = [], [], []

    for token in tokens:
        is_valid, number, error = validate_number(token)
        if not is_valid or number < session.start_number or number > session.end_number:
            invalid.append(token)
        elif number in drawn_numbers:
            matched.append(number)
        elif number in remaining_numbers:
            not_drawn.append(number)
        else:
            invalid.append(token)

    is_winner = len(set(matched)) >= 5 and not not_drawn and not invalid
    lines = []
    if matched: lines.append(f"✅ *Số đã quay*: " + ", ".join(f"`{n}`" for n in sorted(set(matched))))
    if not_drawn: lines.append(f"⭕ *Số chưa quay*: " + ", ".join(f"`{n}`" for n in sorted(set(not_drawn))))
    if invalid: lines.append(f"⚠️ *Không hợp lệ*: " + ", ".join(f"`{n}`" for n in sorted(set(invalid))))
    
    if is_winner:
        display_name = user.full_name or str(user.id)
        winner_set = sorted(set(matched))
        if not hasattr(session, "winners"): session.winners = []
        session.winners.append({"user_id": user.id, "name": display_name, "numbers": winner_set, "time": now.isoformat(timespec="seconds")})
        await session_manager.persist_session(chat_id)
        lines.append(f"\n🏆 *Chúc mừng* {escape_markdown(display_name)} *!* \nVé trúng thưởng: " + ", ".join(f"`{n}`" for n in winner_set))

    target_chat_id = chat_id
    suffix = f":{target_chat_id}"

    keyboard = [[InlineKeyboardButton("🎲 Quay tiếp", callback_data=f"cmd:quay{suffix}")]]
    if is_winner:
        keyboard.append([
            InlineKeyboardButton("🏆 Xem kết quả", callback_data=f"cmd:ket_qua{suffix}"),
            InlineKeyboardButton("🛑 Kết thúc Game", callback_data=f"cmd:ket_thuc{suffix}")
        ])

    await update.message.reply_text(
        "📎 *Kết quả kiểm tra:*\n\n" + "\n".join(lines or ["ℹ️ Không có kết quả."]), 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    last_check_time[key] = now

@queued_handler
async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /kinh"""
    await check_command_logic(update, context)

async def toggle_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /toggle_remove"""
    chat_id = update.effective_chat.id
    session = await session_manager.get_session(chat_id)
    
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
    await session_manager.persist_session(chat_id)

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

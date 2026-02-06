import random
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.constants import COOLDOWN_SPIN_SECONDS, COOLDOWN_CHECK_SECONDS, last_results, WAITING_RESPONSES
from src.bot.utils import (
    escape_markdown, session_manager, ensure_active_session, 
    get_chat_stats, get_last_result_for_chat
)
from src.bot.wheel import spin_wheel
from src.utils.validators import validate_number

logger = logging.getLogger(__name__)

# Runtime state
last_spin_time: dict[int, datetime] = {}
last_check_time: dict[tuple[int, int], datetime] = {}

async def spin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /quay"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)
    
    now = datetime.now()

    if not session:
        await update.message.reply_text(
            "❌ *Chưa có game nào trong chat\\!*\n\nHost dùng `/moi <tên_game>` hoặc `/pham_vi <x> <y>` để tạo game trước nhé\\.",
            parse_mode='Markdown'
        )
        return

    if not await ensure_active_session(update, chat_id, session):
        return

    if not getattr(session, "started", False):
        await update.message.reply_text(
            "⏱️ *Game chưa bắt đầu\\!* \n\nHost cần dùng lệnh `/bat_dau` để bắt đầu game trước khi quay số.",
            parse_mode='Markdown'
        )
        return
    
    try:
        # Phát sinh số và hiển thị kết quả ngay
        number = spin_wheel(session)
        last_spin_time[chat_id] = now
        
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"

        # Hiển thị kết quả
        drawn_numbers = [item.get("number") for item in session.history[-10:]]
        
        # Convert số sang Unicode bold để to hơn
        def to_bold_digits(num):
            """Convert số thành Unicode Mathematical Bold Digits"""
            bold_map = {
                '0': '𝟎', '1': '𝟏', '2': '𝟐', '3': '𝟑', '4': '𝟒',
                '5': '𝟓', '6': '𝟔', '7': '𝟕', '8': '𝟖', '9': '𝟗'
            }
            return ''.join(bold_map.get(c, c) for c in str(num))
        
        bold_number = to_bold_digits(number)
        
        # SỐ TRÚNG THƯỞNG nổi bật với số to
        message = "🎊🎊🎊🎊🎊🎊🎊🎊🎊\n\n"
        message += f"🎯 *SỐ TRÚNG THƯỞNG*\n\n"
        message += f"╔═══════════════╗\n"
        message += f"║      {bold_number}      ║\n"
        message += f"╚═══════════════╝\n\n"
        message += "🎊🎊🎊🎊🎊🎊🎊🎊🎊\n\n"
        
        # Hiển thị lịch sử gần đây theo dọc (mới nhất ở trên)
        if drawn_numbers:
            message += "📜 *Gần đây:*\n"
            for num in reversed(drawn_numbers):
                message += f"   • `{num}`\n"
            message += "\n"
        
        # Kiểm tra và tag người đang đợi số này
        if hasattr(session, 'waiting_numbers') and number in session.waiting_numbers:
            waiters = session.waiting_numbers.pop(number) # Lấy và xóa luôn để không báo lại
            if waiters:
                mentions = []
                for uid, name in waiters:
                    mentions.append(f"[{escape_markdown(name)}](tg://user?id={uid})")
                
                mentions_str = ", ".join(mentions)
                response_template = random.choice(WAITING_RESPONSES)
                # Format: "Á đù, số **23** về rồi kìa! [User] đâu ra nhận hàng!"
                response = response_template.format(number=number, mentions=mentions_str)
                message += f"{response}\n\n"
        
        message += f"📊 Còn lại: `{session.get_remaining_count()}/{session.get_total_numbers()}`"
        
        keyboard = [
            [InlineKeyboardButton("🎲 Quay tiếp", callback_data=f"cmd:quay{suffix}"),
             InlineKeyboardButton("📜 Các số đã ra", callback_data=f"cmd:trang_thai{suffix}")]
        ]
        if session.is_empty():
            message += "\n\n⚠️ Danh sách đã hết\\! Sử dụng `/reset` để làm mới\\."
            keyboard = [[InlineKeyboardButton("🔄 Reset số", callback_data=f"cmd:dat_lai{suffix}")]]
        
        keyboard.append([InlineKeyboardButton("🧾 Kiểm tra vé (/kinh)", switch_inline_query_current_chat="kinh ")])
        keyboard.append([
            InlineKeyboardButton("🛑 Kết thúc Game", callback_data=f"cmd:ket_thuc{suffix}"),
            InlineKeyboardButton("🕹️ Game mới", callback_data=f"cmd:moi_input{suffix}")
        ])

        # Gửi kết quả ngay lập tức
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        session_manager.persist_session(chat_id)
    except ValueError as e:
        await update.message.reply_text(f"❌ {str(e)}")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /dat_lai (reset các số đã quay)"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)
    
    if not session:
        await update.message.reply_text("❌ *Chưa có game nào trong chat\\!*", parse_mode='Markdown')
        return
    
    from src.bot.wheel import reset_session
    reset_session(session)
    session_manager.persist_session(chat_id)

    await update.message.reply_text("🔄 *Đã làm mới danh sách số quay\\!* \n\nGiờ bạn có thể bắt đầu quay từ đầu.", parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /trang_thai"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)
    
    if not session:
        await update.message.reply_text("❌ *Chưa có game nào đang chạy\\!*", parse_mode='Markdown')
        return
    
    drawn = [item.get("number") for item in session.history]
    total = session.get_total_numbers()
    remaining = session.get_remaining_count()
    
    msg = (
        f"📊 *Trạng thái game hiện tại:*\n\n"
        f"🕹️ Game: `{escape_markdown(getattr(session, 'game_name', 'Không tên'))}`\n"
        f"🔄 Vòng: `{escape_markdown(getattr(session, 'round_name', 'Không có'))}`\n"
        f"🔢 Đã quay: `{total - remaining}` / `{total}` số\n"
        f"🎯 Các số đã ra: " + (", ".join(f"`{n}`" for n in sorted(drawn)) if drawn else "_Chưa có_")
    )
    target_chat_id = chat_id
    suffix = f":{target_chat_id}"

    await update.message.reply_text(
        msg, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Quay số", callback_data=f"cmd:quay{suffix}"),
             InlineKeyboardButton("👥 Danh sách", callback_data=f"cmd:danh_sach{suffix}")],
            [InlineKeyboardButton("🛑 Kết thúc Game", callback_data=f"cmd:ket_thuc{suffix}"),
             InlineKeyboardButton("🕹️ Game mới", callback_data=f"cmd:moi_input{suffix}")]
        ])
    )

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /lich_su"""
    chat_id = update.effective_chat.id
    session = session_manager.get_session(chat_id)

    if not session or not session.history:
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"
        await update.message.reply_text(
            "ℹ️ Chưa có lịch sử quay số trong game này.", 
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎲 Quay ngay", callback_data=f"cmd:quay{suffix}")]
            ])
        )
        return

    lines = []
    for idx, item in enumerate(session.history, start=1):
        num = item.get("number")
        time_str = item.get("time", "").split("T")[-1] # Lấy giờ:phút:giây
        lines.append(f"{idx}. Số `{num}` _({time_str})_")

    target_chat_id = chat_id
    suffix = f":{target_chat_id}"

    await update.message.reply_text(
        f"📜 *Lịch sử quay số ({len(session.history)} lượt):*\n\n" + "\n".join(lines),
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Quay tiếp", callback_data=f"cmd:quay{suffix}"),
             InlineKeyboardButton("📋 Menu", callback_data=f"cmd:menu_fallback{suffix}")]
        ])
    )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /xoa - xoá hoàn toàn session"""
    chat_id = update.effective_chat.id
    session_manager.delete_session(chat_id)
    target_chat_id = chat_id
    suffix = f":{target_chat_id}"
    await update.message.reply_text(
        "🗑️ *Đã xoá game hiện tại trong chat này\\.*", 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🕹️ Tạo Game mới", callback_data=f"cmd:moi_input{suffix}")]])
    )

async def lastresult_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /ket_qua"""
    chat_id = update.effective_chat.id
    data = get_last_result_for_chat(chat_id)

    if not data:
        target_chat_id = chat_id
        suffix = f":{target_chat_id}"
        await update.message.reply_text(
            "ℹ️ Chưa có game nào kết thúc trong chat này.", 
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🕹️ Game mới", callback_data=f"cmd:moi_input{suffix}")]
            ])
        )
        return

    game_name = data.get("game_name") or "Không đặt tên"
    host_name = data.get("host_name") or "Host"
    ended_at = data.get("ended_at") or ""
    numbers_drawn = data.get("numbers_drawn") or []
    winners = data.get("winners") or []

    drawn_list = [item.get("number") for item in numbers_drawn if item.get("number") is not None]
    total_spins = len(drawn_list)
    numbers_str = ", ".join(f"`{n}`" for n in drawn_list[-20:]) if drawn_list else "_Chưa quay số nào_"
    if total_spins > 20: numbers_str = f"... , {numbers_str}"

    msg = (
        "📊 *Kết quả game gần nhất:*\n\n"
        f"🕹️ Tên game: `{escape_markdown(str(game_name))}`\n"
        f"⭐ Host: `{escape_markdown(str(host_name))}`\n"
        f"⏱️ Kết thúc: `{escape_markdown(str(ended_at))}`\n"
        f"🎲 Tổng lượt quay: `{total_spins}`\n"
        f"🎯 Một số lần quay gần nhất: {numbers_str}\n\n"
    )

    if winners:
        msg += "🏆 *Người trúng thưởng:*\n"
        for w in winners:
            w_name = escape_markdown(str(w.get("name") or w.get("user_id")))
            nums_str = ", ".join(f"`{n}`" for n in (w.get("numbers") or []))
            msg += f"- {w_name}: {nums_str}\n"
    else:
        msg += "🏆 *Không có ai trúng thưởng\\.*\n"

    target_chat_id = chat_id
    suffix = f":{target_chat_id}"

    await update.message.reply_text(
        msg, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🕹️ Game mới", callback_data=f"cmd:moi_input{suffix}"),
             InlineKeyboardButton("🏆 Xếp hạng", callback_data=f"cmd:xep_hang{suffix}")]
        ])
    )

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /xep_hang"""
    chat_id = update.effective_chat.id
    chat_stats = get_chat_stats(chat_id)

    if not chat_stats:
        await update.message.reply_text("ℹ️ Chưa có dữ liệu thống kê.", parse_mode='Markdown')
        return

    mode = "wins"
    if context.args and (context.args[0].lower().startswith("join") or context.args[0].lower().startswith("part")):
        mode = "participations"

    items = chat_stats.get(mode, {})
    if not items:
        await update.message.reply_text(f"ℹ️ Chưa có dữ liệu {mode}.", parse_mode='Markdown')
        return

    sorted_items = sorted(items.items(), key=lambda kv: kv[1].get("count", 0.0), reverse=True)[:10]
    title = "🏆 *Top người trúng thưởng:*" if mode == "wins" else "👥 *Top người tham gia:*"
    
    lines = []
    for idx, (uid, info) in enumerate(sorted_items, start=1):
        name = escape_markdown(str(info.get("name") or uid))
        count = float(info.get("count", 0.0))
        count_str = str(int(count)) if count.is_integer() else f"{count:.2f}"
        lines.append(f"{idx}. {name} - `{count_str}` lần")

    target_chat_id = chat_id
    suffix = f":{target_chat_id}"

    await update.message.reply_text(
        f"{title}\n\n" + "\n".join(lines) + "\n\nℹ️ Dùng `/xep_hang wins` hoặc `/xep_hang join`.", 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🕹️ Game mới", callback_data=f"cmd:moi_input{suffix}"),
             InlineKeyboardButton("🎲 Quay số", callback_data=f"cmd:quay{suffix}")]
        ])
    )

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /kinh"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    session = session_manager.get_session(chat_id)

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
        session_manager.persist_session(chat_id)
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

async def xoakinh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /xoa_kinh"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    session = session_manager.get_session(chat_id)

    if not session or not getattr(session, "winners", []):
        await update.message.reply_text("❌ Không có vé nào để xoá.", parse_mode="Markdown")
        return

    winners = list(session.winners)
    for i in range(len(winners)-1, -1, -1):
        if winners[i].get("user_id") == user_id:
            removed = winners.pop(i)
            session.winners = winners
            session_manager.persist_session(chat_id)
            nums_str = ", ".join(f"`{n}`" for n in (removed.get("numbers") or []))
            await update.message.reply_text(f"✅ Đã xoá vé trúng thưởng gần nhất của bạn.\n\n🧾 Vé: {nums_str}", parse_mode="Markdown")
            return

    await update.message.reply_text("ℹ️ Bạn chưa có vé trúng thưởng nào.", parse_mode="Markdown")

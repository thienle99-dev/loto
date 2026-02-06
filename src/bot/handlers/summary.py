import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.utils import escape_markdown, session_manager, get_chat_stats
from src.bot.constants import active_rounds, round_history

logger = logging.getLogger(__name__)

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /tong_ket - hiển thị tổng kết các game trong vòng chơi"""
    chat_id = update.effective_chat.id
    
    # Kiểm tra xem có vòng chơi đang hoạt động không
    if chat_id not in active_rounds:
        await update.message.reply_text(
            "ℹ️ *Chưa có vòng chơi nào đang hoạt động\\.*\n\n"
            "Hãy tạo vòng chơi bằng `/vong_moi \u003ctên_vòng\u003e` trước\\.",
            parse_mode='Markdown'
        )
        return
    
    # Lấy thông tin vòng chơi
    round_info = active_rounds[chat_id]
    round_name = round_info.get("round_name", "Không tên")
    created_at = round_info.get("created_at", "Không rõ")
    
    # Lấy lịch sử các game trong vòng
    games = round_history.get(chat_id, [])
    
    if not games:
        await update.message.reply_text(
            f"📊 *TỔNG KẾT VÒNG*\n\n"
            f"🔄 *Vòng:* `{escape_markdown(round_name)}`\n"
            f"🕐 *Tạo lúc:* `{created_at[:19]}`\n\n"
            "ℹ️ *Chưa có game nào kết thúc trong vòng này\\.*\n\n"
            "Hãy chơi và kết thúc ít nhất một game trước\\.",
            parse_mode='Markdown'
        )
        return
    
    # Lấy thống kê token
    chat_stats = get_chat_stats(chat_id)
    wins = chat_stats.get("wins", {})
    
    # Tạo message tổng kết
    message = "📊 *TỔNG KẾT VÒNG CHƠI*\n\n"
    message += "━━━━━━━━━━━━━━━━━━━\n\n"
    message += f"🔄 *Vòng:* `{escape_markdown(round_name)}`\n"
    message += f"🕐 *Tạo lúc:* `{created_at[:19]}`\n"
    message += f"🎮 *Tổng số game:* `{len(games)}`\n\n"
    message += "━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Hiển thị từng game
    for i, game in enumerate(games, 1):
        game_name = game.get("game_name", f"Game {i}")
        host_name = game.get("host_name", "Không rõ")
        winners = game.get("winners", [])
        participants = game.get("participants", [])
        numbers_drawn = game.get("numbers_drawn", 0)
        ended_at = game.get("ended_at", "")
        
        message += f"🕹️ *GAME {i}: {escape_markdown(game_name)}*\n"
        message += f"👤 Host: {escape_markdown(host_name)}\n"
        message += f"🎲 Số lần quay: `{numbers_drawn}`\n"
        if ended_at:
            message += f"🕐 Kết thúc: `{ended_at[:19]}`\n"
        message += "\n"
        
        # Người thắng
        if winners:
            message += "🏆 *Người thắng:*\n"
            for winner in winners:
                name = winner.get("name", "Không rõ")
                numbers = winner.get("numbers", [])
                nums_str = ", ".join(f"`{n}`" for n in numbers) if numbers else "N/A"
                message += f"   • {escape_markdown(name)}: {nums_str}\n"
        else:
            message += "   ℹ️ Không có người thắng\n"
        message += "\n"
        
        # Người tham gia với token
        if participants:
            message += "👥 *Người chơi:*\n"
            for p in participants:
                name = p.get("name", "Không rõ")
                uid = p.get("user_id")
                token_count = wins.get(uid, {}).get("count", 0.0) if uid else 0.0
                token_str = f" \\- Token: `{token_count:+.1f}`" if token_count != 0 else " \\- Token: `0.0`"
                message += f"   • {escape_markdown(name)}{token_str}\n"
        message += "\n"
        
        message += "━━━━━━━━━━━━━━━━━━━\n\n"
    
    target_chat_id = chat_id
    suffix = f":{target_chat_id}"
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🕹️ Game mới", callback_data=f"cmd:moi_input{suffix}"),
             InlineKeyboardButton("🏁 Kết thúc Vòng", callback_data=f"cmd:ket_thuc_vong{suffix}")]
        ])
    )

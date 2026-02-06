import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.utils import escape_markdown, get_chat_stats

logger = logging.getLogger(__name__)

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /xep_hang - Xem bảng xếp hạng Token"""
    chat_id = update.effective_chat.id
    
    # Lấy thống kê
    chat_stats = get_chat_stats(chat_id)
    wins = chat_stats.get("wins", {})
    
    # Chỉ lấy những người có biến động token (khác 0)
    players = []
    for uid, info in wins.items():
        count = info.get("count", 0.0)
        if count != 0:
            name = info.get("name", str(uid))
            players.append({"name": name, "token": count})
            
    if not players:
        await update.message.reply_text(
            "📊 *Bảng Xếp Hạng Token*\n\n"
            "Chưa có dữ liệu biến động token nào.\n"
            "Hãy chơi vài ván để tích lũy điểm nhé!",
            parse_mode='Markdown'
        )
        return

    # Sắp xếp
    top_rich = sorted(players, key=lambda x: x["token"], reverse=True)[:5]
    top_poor = sorted(players, key=lambda x: x["token"])[:5]
    
    # Loại bỏ những người có token >= 0 khỏi top xa bờ (chỉ lấy người âm)
    top_poor = [p for p in top_poor if p["token"] < 0]
    
    message = "🏆 *BẢNG XẾP HẠNG TOKEN*\n"
    message += "━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Top Đại Gia
    message += "💎 *TOP ĐẠI GIA (Nhiều Token nhất):*\n"
    if top_rich:
        for i, p in enumerate(top_rich, 1):
            token = p["token"]
            prefix = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            message += f"{prefix} {escape_markdown(p['name'])}: `+{token:.1f}`\n"
    else:
        message += "_(Chưa có ai)_\n"
    message += "\n"
    
    # Top Xa Bờ
    message += "🌊 *TOP XA BỜ (Âm nhiều nhất):*\n"
    if top_poor:
        for i, p in enumerate(top_poor, 1):
            token = p["token"]
            # Đảo ngược thứ tự hiển thị để người âm nhiều nhất đứng đầu (đã sort asc ở trên)
            message += f"{i}. {escape_markdown(p['name'])}: `{token:.1f}`\n"
    else:
        message += "_(Tất cả đều đang lời hoặc hòa)_\n"
        
    message += "\n━━━━━━━━━━━━━━━━━━━"

    target_chat_id = chat_id
    suffix = f":{target_chat_id}"

    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🕹️ Game mới", callback_data=f"cmd:moi_input{suffix}"),
             InlineKeyboardButton("🔄 Vòng mới", callback_data=f"cmd:vong_moi_input{suffix}")]
        ])
    )

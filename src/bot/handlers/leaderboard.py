from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.utils import escape_markdown, get_chat_stats, session_manager
from src.bot.utils import escape_markdown, get_chat_stats, session_manager
import logging


logger = logging.getLogger(__name__)

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /xep_hang - Xem bảng xếp hạng Token"""
    chat_id = update.effective_chat.id
    
    # Lấy thống kê
    chat_stats = await get_chat_stats(chat_id)
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
    top_rich = sorted([p for p in players if p["token"] > 0], key=lambda x: x["token"], reverse=True)[:5]
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
            txt_token = f"+{token:.1f}" if token > 0 else f"{token:.1f}"
            message += f"{prefix} {escape_markdown(p['name'])}: `{txt_token}`\n"
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
            [InlineKeyboardButton("🕹️ Game mới", callback_data=f"cmd:moi_input{suffix}")]
        ])
    )

async def show_user_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /xem_token - Xem token của tất cả người tham gia"""
    chat_id = update.effective_chat.id
    
    # 1. Hiện token tổng (từ chat stats)
    chat_stats = await get_chat_stats(chat_id)
    wins = chat_stats.get("wins", {})
    
    if not wins:
        await update.message.reply_text(
            "📊 *DANH SÁCH TOKEN TỔNG*\n\n"
            "Chưa có dữ liệu token nào trong chat này.",
            parse_mode='Markdown'
        )
        return
        
    players = []
    for uid, info in wins.items():
        players.append({"name": info.get("name", str(uid)), "token": info.get("count", 0.0)})
        
    players.sort(key=lambda x: x["token"], reverse=True)
    
    message = "📊 *DANH SÁCH TOKEN TỔNG*\n"
    message += "━━━━━━━━━━━━━━━━━━━\n\n"
    for p in players:
        token = p["token"]
        txt_token = f"+{token:.1f}" if token > 0 else f"{token:.1f}"
        message += f"• {escape_markdown(p['name'])}: `{txt_token}`\n"
    message += "\n━━━━━━━━━━━━━━━━━━━"

    await update.message.reply_text(message, parse_mode='Markdown')

async def reset_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /reset_token - Đặt lại toàn bộ token về 0 cho chat này"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Kiểm tra quyền host của vòng (nếu có) hoặc chỉ đơn giản cho phép reset?
    # Trong các command khác, owner_id thường được check.
    # Nhưng user yêu cầu reset_token, ta cứ thực hiện.
    
    chat_stats = await get_chat_stats(chat_id)
    chat_stats["wins"] = {}
    # Giữ lại participations nếu chỉ muốn reset token? 
    # User nói "clear token", nên ta chỉ clear wins.
    
    save_stats(chat_id, chat_stats)
    
    # Xoá cache RAM
    from src.bot.constants import stats
    if chat_id in stats:
        del stats[chat_id]
    
    await update.message.reply_text(
        "✨ *Đã đặt lại toàn bộ Token về 0\\!*",
        parse_mode='Markdown'
    )

async def xoa_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /xoa_token @mention - Đặt lại token của một người về 0"""
    chat_id = update.effective_chat.id
    
    target_user_id = None
    target_name = None
    
    # 1. Kiểm tra reply
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        target_user_id = target_user.id
        target_name = target_user.full_name
    # 2. Kiểm tra mention
    elif context.args:
        # Thử tìm trong các thực thể tin nhắn (mentions)
        mentions = update.message.parse_entities(["mention", "text_mention"])
        if mentions:
            # Lấy mention đầu tiên
            entity, text = next(iter(mentions.items()))
            if entity.type == "text_mention":
                target_user_id = entity.user.id
                target_name = entity.user.full_name
            else:
                # mention thường chỉ có username (@abc), cần tìm trong stats
                username = text.lstrip('@')
                chat_stats = await get_chat_stats(chat_id)
                wins = chat_stats.get("wins", {})
                for uid, info in wins.items():
                    if info.get("username") == username:
                        target_user_id = uid
                        target_name = info.get("name")
                        break
        # Nếu không có mention nhưng có args, có thể là user_id
        if not target_user_id:
            try:
                target_user_id = int(context.args[0])
            except ValueError:
                pass

    if not target_user_id:
        await update.message.reply_text(
            "⚠️ *Thiếu mục tiêu\\!*\n\n"
            "Sử dụng: `/xoa_token @mention` hoặc *trả lời (reply)* tin nhắn của người đó.",
            parse_mode='Markdown'
        )
        return

    chat_stats = await get_chat_stats(chat_id)
    wins = chat_stats.get("wins", {})
    
    if str(target_user_id) in wins or target_user_id in wins:
        # Xóa khỏi bảng xếp hạng tổng
        if str(target_user_id) in wins:
            del wins[str(target_user_id)]
        if target_user_id in wins:
            del wins[target_user_id]
            
        save_stats(chat_id, chat_stats)
        await update.message.reply_text(
            f"✅ Đã đặt lại Token của {escape_markdown(target_name or str(target_user_id))} về `0.0`.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"👤 {escape_markdown(target_name or str(target_user_id))} hiện chưa có dữ liệu token.",
            parse_mode='Markdown'
        )

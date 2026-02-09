from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.utils import escape_markdown, get_chat_stats, session_manager
from src.bot.constants import round_history, active_rounds
from src.db.sqlite_store import save_stats
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
            [InlineKeyboardButton("🕹️ Game mới", callback_data=f"cmd:moi_input{suffix}"),
             InlineKeyboardButton("🔄 Vòng mới", callback_data=f"cmd:vong_moi_input{suffix}")]
        ])
    )

async def leaderboard_round_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /xep_hang_vong - Xem BXH trong vòng chơi hiện tại"""
    chat_id = update.effective_chat.id
    
    if chat_id not in active_rounds:
        await update.message.reply_text("⚠️ Chưa có vòng chơi nào đang diễn ra.")
        return
        
    round_info = active_rounds[chat_id]
    round_name = round_info.get("round_name", "Hiện tại")
    
    games = round_history.get(chat_id, [])
    if not games:
        await update.message.reply_text("ℹ️ Chưa có game nào kết thúc trong vòng này.")
        return
        
    # Tính toán và lấy text BXH
    from src.bot.utils import calculate_round_tokens, get_round_leaderboard_text
    user_tokens = calculate_round_tokens(games)
    message = get_round_leaderboard_text(round_name, user_tokens)
    
    target_chat_id = chat_id
    suffix = f":{target_chat_id}"
    
    await update.message.reply_text(
        message, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏁 Kết thúc Vòng", callback_data=f"cmd:ket_thuc_vong{suffix}")]
        ])
    )

async def show_user_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /xem_token - Xem token của tất cả người tham gia"""
    chat_id = update.effective_chat.id
    
    # 1. Kiểm tra nếu có vòng chơi
    if chat_id in active_rounds:
        round_info = active_rounds[chat_id]
        round_name = round_info.get("round_name", "Hiện tại")
        games = round_history.get(chat_id, [])
        
        logger.info(f"[/xem_token] Chat {chat_id}: Round '{round_name}', {len(games)} games in history")
        
        from src.bot.utils import calculate_round_tokens
        user_tokens = calculate_round_tokens(games)
        
        logger.info(f"[/xem_token] Calculated tokens for {len(user_tokens)} users")
        
        # Kiểm tra nếu có game đang chơi
        session = await session_manager.get_session(chat_id)
        has_active_game = session is not None
        
        if not user_tokens:
            # Phân biệt giữa "chưa có game nào kết thúc" vs "vòng rỗng"
            if has_active_game:
                await update.message.reply_text(
                    f"📊 *DANH SÁCH TOKEN VÒNG: {escape_markdown(round_name)}*\n\n"
                    "ℹ️ Vòng mới bắt đầu\\. Hãy kết thúc ván đầu tiên bằng `/ket_thuc` để xem token\\!\n\n"
                    "📝 _Game hiện tại chưa được tính vào tổng\\._",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"📊 *DANH SÁCH TOKEN VÒNG: {escape_markdown(round_name)}*\n\n"
                    "ℹ️ Chưa có game nào kết thúc trong vòng này\\.",
                    parse_mode='Markdown'
                )
            return

        players = sorted(user_tokens.values(), key=lambda x: x["token"], reverse=True)
        message = f"📊 *DANH SÁCH TOKEN VÒNG: {escape_markdown(round_name)}*\n"
        message += "━━━━━━━━━━━━━━━━━━━\n\n"
        
        for p in players:
            token = p["token"]
            txt_token = f"+{token:.1f}" if token > 0 else f"{token:.1f}"
            message += f"• {escape_markdown(p['name'])}: `{txt_token}`\n"
            
        message += "\n━━━━━━━━━━━━━━━━━━━"
        
        # Thêm ghi chú nếu có game đang chơi
        if has_active_game:
            message += "\n\n📝 _Game hiện tại chưa được tính vào tổng\\._"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        return

    # 2. Nếu không có vòng, hiện token tổng (từ chat stats)
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

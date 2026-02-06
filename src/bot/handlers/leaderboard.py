from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.utils import escape_markdown, get_chat_stats
from src.bot.constants import round_history, active_rounds
import logging


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
        
    # Tính toán token
    user_tokens = {} # {uid: {"name": name, "token": float}}
    
    for game in games:
        partics = game.get("participants", [])
        winners = game.get("winners", [])
        total_players = len(partics)
        
        # Xác định winners ID
        winner_ids = {w.get("user_id") for w in winners if w.get("user_id") is not None}
        num_winners = len(winner_ids)
        
        bet_amount = 5.0
        
        if num_winners > 0:
            token_win = (total_players * bet_amount / num_winners) - bet_amount
        else:
            token_win = 0 # Không ai thắng thì không tính? Hoặc tính kiểu khác. Hiện tại giả sử luôn có người thắng nếu game end.
            
        for p in partics:
            uid = p.get("user_id")
            if uid is None: continue
            name = p.get("name") or str(uid)
            
            if uid not in user_tokens:
                user_tokens[uid] = {"name": name, "token": 0.0}
            
            # Update name mới nhất
            user_tokens[uid]["name"] = name
            
            if uid in winner_ids:
                user_tokens[uid]["token"] += token_win
            else:
                user_tokens[uid]["token"] -= bet_amount
                
    # Hiển thị BXH
    players = list(user_tokens.values())
    if not players:
        await update.message.reply_text("Chưa có dữ liệu người chơi.")
        return

    top_rich = sorted(players, key=lambda x: x["token"], reverse=True)[:5]
    top_poor = sorted(players, key=lambda x: x["token"])[:5]
    top_poor = [p for p in top_poor if p["token"] < 0]

    message = f"🏆 *BXH TOKEN VÒNG: {escape_markdown(round_name)}*\n"
    message += "━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Top Đại Gia
    message += "💎 *TOP ĐẠI GIA:*\n"
    if top_rich:
        for i, p in enumerate(top_rich, 1):
            token = p["token"]
            prefix = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            txt_token = f"+{token:.1f}" if token > 0 else f"{token:.1f}"
            message += f"{prefix} {escape_markdown(p['name'])}: `{txt_token}`\n"
    else:
        message += "_(Chưa cón ai)_\n"
    message += "\n"
    
    # Top Xa Bờ
    message += "🌊 *TOP XA BỜ:*\n"
    if top_poor:
        for i, p in enumerate(top_poor, 1):
            token = p["token"]
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
            [InlineKeyboardButton("🏁 Kết thúc Vòng", callback_data=f"cmd:ket_thuc_vong{suffix}")]
        ])
    )

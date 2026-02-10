from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.utils import escape_markdown, get_chat_stats, session_manager, save_stats
import logging
import asyncio


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

async def bao_danh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback xử lý khi user nhấn nút Báo danh"""
    query = update.callback_query
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    if user.is_bot:
        await query.answer("🤖 Bot không cần báo danh.")
        return

    chat_stats = await get_chat_stats(chat_id)
    wins = chat_stats.get("wins", {})
    
    uid = user.id
    if str(uid) not in wins and uid not in wins:
        wins[uid] = {
            "count": 0.0,
            "name": user.full_name,
            "username": user.username,
            "is_bot": False
        }
        await asyncio.to_thread(save_stats, chat_id, chat_stats)
        await query.answer(f"✅ Đã ghi nhận: {user.full_name}!")
        # Refres lại danh sách
        await show_user_token_command(update, context)
    else:
        await query.answer("✨ Bạn đã có tên trong danh sách rồi!")

async def show_user_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /xem_token - Xem token của tất cả người tham gia"""
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    is_callback = update.callback_query is not None
    user = update.effective_user
    
    # Hỗ trợ xem token từ xa trong Private Chat: /xem_token <chat_id>
    target_chat_id = chat_id
    is_remote = False
    if chat_type == 'private' and context.args:
        try:
            target_chat_id = int(context.args[0])
            is_remote = True
        except ValueError:
            pass

    # 1. Lấy thông tin member count (nếu là group)
    human_count = 0
    try:
        # Lấy type của target chat
        target_chat = await context.bot.get_chat(target_chat_id)
        if target_chat.type in ['group', 'supergroup']:
            total_count = await context.bot.get_chat_member_count(target_chat_id)
            human_count = max(1, total_count - 1)
    except:
        pass

    # 2. Hiện token tổng (từ chat stats)
    chat_stats = await get_chat_stats(target_chat_id)
    wins = chat_stats.get("wins", {})
    participations = chat_stats.get("participations", {})
    
    # Merge participations vào danh sách nếu họ chưa có trong wins (token = 0)
    for uid, info in participations.items():
        if str(uid) not in wins and uid not in wins:
            wins[uid] = {
                "count": 0.0,
                "name": info.get("name", str(uid)),
                "username": info.get("username"),
                "is_bot": False
            }

    has_updates = False
    
    # 3. Thêm Admin vào danh sách (Chỉ khi không phải remote hoặc remote access được)
    try:
        admins = await context.bot.get_chat_administrators(target_chat_id)
        for member in admins:
            u = member.user
            if u.is_bot: continue
            uid = u.id
            if str(uid) not in wins and uid not in wins:
                wins[uid] = {
                    "count": 0.0,
                    "name": u.full_name,
                    "username": u.username,
                    "is_bot": False
                }
                has_updates = True
            else:
                info = wins.get(str(uid)) or wins.get(uid)
                if info:
                    if info.get("name") != u.full_name or info.get("username") != u.username:
                        info["name"] = u.full_name
                        info["username"] = u.username
                        info["is_bot"] = False
                        has_updates = True
    except Exception as e:
        logger.warning(f"Không thể lấy danh sách admin cho chat {target_chat_id}: {e}")

    # 4. Thêm Participants từ session hiện tại
    session = await session_manager.get_session(target_chat_id)
    if session:
        participants = session.get_participants()
        for p in participants:
            uid = p.get("user_id")
            if not uid: continue
            if str(uid) not in wins and uid not in wins:
                wins[uid] = {
                    "count": 0.0,
                    "name": p.get("name", str(uid)),
                    "username": None,
                    "is_bot": False
                }
                has_updates = True

    # 5. Lưu nếu có update
    if has_updates:
        await asyncio.to_thread(save_stats, target_chat_id, chat_stats)

    players = []
    for uid, info in wins.items():
        if info.get("is_bot"): continue
        players.append({"name": info.get("name", str(uid)), "token": info.get("count", 0.0)})
        
    players.sort(key=lambda x: x["token"], reverse=True)
    recorded_count = len(players)
    
    # Thêm placeholder cho những thành viên chưa được bot "thấy"
    if human_count > recorded_count:
        gap = human_count - recorded_count
        for _ in range(gap):
            players.append({"name": "❔ (Chưa báo danh)", "token": 0.0})
    
    # Build Header
    try:
        title = (await context.bot.get_chat(target_chat_id)).title or "Nhóm"
    except:
        title = "Nhóm"

    header = f"📊 *TOKEN TỔNG:* `{escape_markdown(title)}`"
    if human_count > 0:
        header += f"\n👥 (Sĩ số: {human_count})"
    
    if not players:
        message = f"{header}\n\nChưa có dữ liệu token nào."
    else:
        message = f"{header}\n"
        message += "━━━━━━━━━━━━━━━━━━━\n\n"
        for p in players:
            token = p["token"]
            txt_token = f"+{token:.1f}" if token > 0 else f"{token:.1f}"
            message += f"• {escape_markdown(p['name'])}: `{txt_token}`\n"
        message += "\n━━━━━━━━━━━━━━━━━━━"

    # Nút Báo danh nếu còn thiếu member (Chỉ hiện khi ở trong group đó)
    keyboard = []
    if not is_remote and human_count > recorded_count:
        keyboard.append([InlineKeyboardButton("🙋 Báo danh (Hiện tên)", callback_data="bao_danh")])

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    if is_callback:
        await update.callback_query.message.edit_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

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

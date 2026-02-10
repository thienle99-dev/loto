from telegram import Update
from telegram.ext import ContextTypes
from config.config import ADMIN_IDS
from src.db.sqlite_store import get_all_users
from src.bot.utils import escape_markdown
import asyncio

async def account_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /account_list - Chỉ dành cho Admin trong chat riêng tư"""
    user = update.effective_user
    chat = update.effective_chat
    
    # 1. Kiểm tra Admin
    if user.id not in ADMIN_IDS:
        # Không thông báo gì nếu không phải admin để bảo mật, hoặc báo lỗi nhẹ
        return

    # 2. Kiểm tra Chat riêng tư (Private)
    if chat.type != 'private':
        await update.message.reply_text("⚠️ Lệnh này chỉ có thể thực hiện trong chat riêng tư với bot.")
        return

    # 3. Lấy danh sách user
    users = await asyncio.to_thread(get_all_users)
    
    if not users:
        await update.message.reply_text("ℹ️ Chưa có người dùng nào trong cơ sở dữ liệu.")
        return

    message = "👤 *DANH SÁCH TÀI KHOẢN ĐÃ THAM GIA*\n"
    message += "━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, u in enumerate(users, 1):
        uid = u.get("user_id")
        cid = u.get("chat_id")
        name = u.get("name") or "Unknown"
        message += f"{i}. {escape_markdown(name)} (`{uid}`) | Chat: `{cid}`\n"
        
    message += "\n━━━━━━━━━━━━━━━━━━━\n"
    message += f"Tổng cộng: `{len(users)}` người chơi."

    # Chia nhỏ tin nhắn nếu quá dài (Telegram limit 4096 chars)
    if len(message) > 4000:
        # Tạm thời chỉ gửi đoạn đầu nếu quá dài, hoặc có thể implement phân trang sau
        message = message[:4000] + "\n\n...(Còn tiếp)..."

    await update.message.reply_text(message, parse_mode='Markdown')

async def set_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /set_token - Chỉ dành cho Admin"""
    user = update.effective_user
    chat = update.effective_chat
    
    # 1. Kiểm tra Admin
    if user.id not in ADMIN_IDS:
        return

    # 2. Phân tích tham số
    # Syntax: /set_token <user_id> <chat_id> <amount> (Private)
    # Hoặc: /set_token <mention|reply> <amount> (Group)
    
    target_user_id = None
    target_chat_id = chat.id
    amount = None
    
    if chat.type == 'private':
        # Cần 3 tham số trong private chat
        if len(context.args) < 3:
            await update.message.reply_text(
                "⚠️ *Sai cú pháp\\!*\n\n"
                "Trong chat riêng tư, hãy dùng: `/set_token <user_id> <chat_id> <amount>`",
                parse_mode='Markdown'
            )
            return
        try:
            target_user_id = int(context.args[0])
            target_chat_id = int(context.args[1])
            amount = float(context.args[2])
        except ValueError:
            await update.message.reply_text("⚠️ User ID, Chat ID phải là số và Amount phải là số thực.")
            return
    else:
        # Trong group chat, có thể dùng mention/reply
        if update.message.reply_to_message:
            target_user_id = update.message.reply_to_message.from_user.id
            if context.args:
                try: amount = float(context.args[0])
                except: pass
        elif context.args:
            # Check for mention or user_id + amount
            if len(context.args) >= 2:
                # Thử /set_token <user_id> <amount>
                try:
                    target_user_id = int(context.args[0])
                    amount = float(context.args[1])
                except ValueError:
                    # Có thể là mention
                    pass
            
            if target_user_id is None:
                # Thử tìm mention
                mentions = update.message.parse_entities(["mention", "text_mention"])
                if mentions:
                    entity, text = next(iter(mentions.items()))
                    if entity.type == "text_mention":
                        target_user_id = entity.user.id
                    else:
                        # Cần search database theo username (phức tạp hơn, tạm thời chỉ support reply/ID/text_mention)
                        pass
                    
                    try: amount = float(context.args[-1])
                    except: pass

    if target_user_id is None or amount is None:
        await update.message.reply_text(
            "⚠️ *Thiếu thông tin\\!*\n\n"
            "Group: `/set_token @mention 100` hoặc reply tin nhắn kèm số tiền.\n"
            "Private: `/set_token <user_id> <chat_id> <amount>`",
            parse_mode='Markdown'
        )
        return

    # 3. Cập nhật database
    from src.db.sqlite_store import update_user_token
    from src.bot.constants import stats
    
    await asyncio.to_thread(update_user_token, target_chat_id, target_user_id, amount)
    
    # Xoá cache trong RAM để update ngay lập tức
    if target_chat_id in stats:
        del stats[target_chat_id]
        
    await update.message.reply_text(
        f"✅ Đã đặt token cho User `{target_user_id}` trong Chat `{target_chat_id}` thành `{amount:.1f}`.",
        parse_mode='Markdown'
    )

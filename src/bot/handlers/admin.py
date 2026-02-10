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
        name = u.get("name") or "Unknown"
        message += f"{i}. {escape_markdown(name)} (`{uid}`)\n"
        
    message += "\n━━━━━━━━━━━━━━━━━━━\n"
    message += f"Tổng cộng: `{len(users)}` người chơi."

    # Chia nhỏ tin nhắn nếu quá dài (Telegram limit 4096 chars)
    if len(message) > 4000:
        # Tạm thời chỉ gửi đoạn đầu nếu quá dài, hoặc có thể implement phân trang sau
        message = message[:4000] + "\n\n...(Còn tiếp)..."

    await update.message.reply_text(message, parse_mode='Markdown')

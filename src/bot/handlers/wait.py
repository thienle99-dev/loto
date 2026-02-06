import logging
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.utils import session_manager
from src.utils.validators import validate_number

logger = logging.getLogger(__name__)

async def wait_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho lệnh /doi <số 1> <số 2> ... - Đăng ký đợi số"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    args = context.args
    
    session = session_manager.get_session(chat_id)
    if not session:
        await update.message.reply_text("⚠️ Chưa có game nào đang diễn ra! Hãy tạo game mới bằng `/moi`.")
        return

    if not args:
        await update.message.reply_text("⚠️ Vui lòng nhập danh sách số bạn muốn đợi. Ví dụ: `/doi 10 25 90`")
        return

    try:
        # Parse và validate số
        waiting_list = []
        invalid_list = []
        already_drawn = []
        
        # Lấy danh sách số đã xổ
        drawn_numbers = set()
        if session.history:
            for item in session.history:
                drawn_numbers.add(item.get("number"))
        
        for arg in args:
            if arg.isdigit():
                num = int(arg)
                if not validate_number(num, session.start_number, session.end_number):
                    invalid_list.append(arg)
                    continue
                    
                # Kiểm tra xem số đã quay chưa
                if num in drawn_numbers:
                    already_drawn.append(num)
                    continue
                    
                waiting_list.append(num)
            else:
                invalid_list.append(arg)
    
        if not waiting_list and not already_drawn:
            # Nếu người dùng nhập toàn số sai hoặc không nhập gì hợp lệ
            if invalid_list:
                await update.message.reply_text(f"❌ Số không hợp lệ: {', '.join(invalid_list)}")
            else:
                await update.message.reply_text("⚠️ Không tìm thấy số hợp lệ để đợi.")
            return
    
        # Lưu vào session
        # Đảm bảo waiting_numbers tồn tại (kể cả session cũ)
        if not hasattr(session, 'waiting_numbers'):
            session.waiting_numbers = {}

        count = 0
        display_name = user.full_name or str(user.id)
        user_info = (user.id, display_name)
        
        for num in waiting_list:
            if num not in session.waiting_numbers:
                session.waiting_numbers[num] = []
            
            # Kiểm tra xem đã đăng ký chưa để tránh duplicate
            is_exist = False
            for uid, uname in session.waiting_numbers[num]:
                if uid == user.id:
                    is_exist = True
                    break
            
            if not is_exist:
                session.waiting_numbers[num].append(user_info)
                count += 1
                
        session_manager.persist_session(chat_id)
    
        # Tạo message phản hồi
        msg_parts = []
        if count > 0:
            msg_parts.append(f"✅ Đã đăng ký đợi {count} số: " + ", ".join(f"`{n}`" for n in waiting_list))
        
        if already_drawn:
            msg_parts.append(f"⚠️ Các số sau ĐÃ ra rồi: " + ", ".join(f"`{n}`" for n in already_drawn))
            
        if invalid_list:
            msg_parts.append(f"❌ Số không hợp lệ: " + ", ".join(invalid_list))
            
        await update.message.reply_text("\n".join(msg_parts), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in wait_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Có lỗi xảy ra khi xử lý lệnh đợi.")

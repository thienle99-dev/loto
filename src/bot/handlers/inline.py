from uuid import uuid4
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes
from src.bot.utils import session_manager
from src.bot.constants import TICKET_DISPLAY_NAMES

async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý Inline Query (ví dụ: @bot kinh 1 2 3)"""
    query = update.inline_query.query.strip().lower()
    user = update.inline_query.from_user
    
    if not query:
        return

    # Chỉ xử lý lệnh "kinh"
    if query.startswith("kinh"):
        # Lấy danh sách số
        args = query.split()[1:]
        if not args:
            return # Chưa nhập số
            
        # Tìm các game đang tham gia
        active_sessions = session_manager.get_sessions_containing_user(user.id)
        
        results = []
        
        if not active_sessions:
            # Không tìm thấy game
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title="⚠️ Không tìm thấy game đang tham gia",
                    input_message_content=InputTextMessageContent(
                        "⚠️ *Bạn hiện không tham gia ván Loto nào đang diễn ra.*\n"
                        "Hãy vào nhóm chat và tham gia game trước!",
                        parse_mode="Markdown"
                    ),
                    description="Bạn cần tham gia game trước khi kinh."
                )
            )
        else:
            # Có game, xử lý từng game (thường chỉ 1)
            for chat_id, session in active_sessions:
                game_name = getattr(session, "game_name", "Loto")
                
                # Logic check số
                found = []
                missing = []
                invalid = []
                
                # History (các số đã ra)
                drawn_numbers = set()
                if session.history:
                    for item in session.history:
                        drawn_numbers.add(item.get("number"))
                
                ticket_code = session.user_tickets.get(user.id)
                ticket_name = TICKET_DISPLAY_NAMES.get(ticket_code, "Vé tự chọn") if ticket_code else "Vé tự do"

                for arg in args:
                    if arg.isdigit():
                        num = int(arg)
                        # Validate range? (Tạm bỏ qua range check chặt chẽ, chỉ check kết quả)
                        if num in drawn_numbers:
                            found.append(num)
                        else:
                            missing.append(num)
                    else:
                        invalid.append(arg)
                
                # Tạo nội dung trả về
                result_text = f"🧾 *KINH! - {game_name}*\n"
                result_text += f"👤 Người hô: {user.full_name}\n"
                result_text += f"🎟️ Loại vé: {ticket_name}\n\n"
                
                if found:
                    result_text += f"✅ *Có ({len(found)}):* " + ", ".join(f"`{n}`" for n in found) + "\n"
                if missing:
                    result_text += f"❌ *Thiếu ({len(missing)}):* " + ", ".join(f"`{n}`" for n in missing) + "\n"
                
                if not missing and found:
                    result_text += "\n🎉 *KINH THÀNH CÔNG! ĐỦ SỐ RỒI!* 🎉"
                elif missing:
                    result_text += "\n⚠️ *Kinh xịt! Chưa đủ số.*"
                
                results.append(
                    InlineQueryResultArticle(
                        id=str(uuid4()),
                        title=f"Kinh: {game_name}",
                        input_message_content=InputTextMessageContent(result_text, parse_mode="Markdown"),
                        description=f"Có: {len(found)} | Thiếu: {len(missing)}",
                    )
                )

        await update.inline_query.answer(results, cache_time=1)

""" 
Telegram bot handlers và commands 
""" 
import logging
import sys
from pathlib import Path
from telegram import Update, MenuButtonWebApp, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from config.config import WEB_APP_URL

# Thêm thư mục gốc vào PYTHONPATH nếu chưa có
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Import basic handlers
from src.bot.handlers.base import (
    start_command, 
    help_command, 
    menu_command, 
    generic_command_callback, 
    handle_force_reply
)

# Import game handlers
from src.bot.handlers.game import (
    vongmoi_command,
    endround_command,
    newsession_command,
    setrange_command,
    startsession_command,
    endsession_command,
    toggle_remove_command
)

# Import player handlers
from src.bot.handlers.player import (
    join_command,
    out_command,
    players_command,
    layve_command,
    lay_ve_callback
)

# Import spin/status handlers
from src.bot.handlers.spin import (
    spin_command,
    reset_command,
    status_command,
    history_command,
    clear_command,
    lastresult_command,
    leaderboard_command,
    check_command,
    xoakinh_command
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý dữ liệu gửi về từ Web App"""
    import json
    data = update.effective_message.web_app_data.data
    try:
        payload = json.loads(data)
        action = payload.get("action")
        
        # Xử lý các action từ Web App
        if action == "lay_ve":
            ticket_id = payload.get("ticket_id")
            context.args = [ticket_id]
            from src.bot.handlers.player import layve_command
            await layve_command(update, context)
            
        elif action == "quay":
             pass # Chỉ host mới quay được, user gửi lệnh này cũng ko sao vì handler check quyền
             
    except Exception as e:
        logger.error(f"Error handling Web App data: {e}")

def setup_bot(token: str) -> Application:
    """Setup và trả về Application instance"""
    async def post_init(application: Application) -> None:
        await application.bot.set_my_commands([
            ("start", "Hướng dẫn"),
            ("menu", "Menu riêng tư (Private)"),
            ("vong_moi", "Tạo vòng chơi mới"),
            ("ket_thuc_vong", "Kết thúc vòng chơi"),
            ("moi", "Tạo game mới"),
            ("quay", "Quay số"),
            ("kinh", "Kiểm tra vé (Kinh!)"),
            ("danh_sach", "Người chơi"),
            ("lay_ve", "Chọn màu vé"),
            ("trang_thai", "Trạng thái"),
            ("ket_thuc", "Kết thúc game"),
            ("tro_giup", "Trợ giúp")
        ])
        
        # Thiết lập Menu Button Web App
        if WEB_APP_URL:
            try:
                await application.bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(text="🎮 Open Loto UI", web_app=WebAppInfo(url=WEB_APP_URL))
                )
            except Exception as e:
                logger.warning(f"⚠️ Không thể thiết lập Menu Web App (có thể do URL không phải HTTPS): {e}")

    application = Application.builder().token(token).post_init(post_init).build()
    
    # Base commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))

    # Game management
    application.add_handler(CommandHandler("vong_moi", vongmoi_command))
    application.add_handler(CommandHandler("ket_thuc_vong", endround_command))
    application.add_handler(CommandHandler("moi", newsession_command))
    application.add_handler(CommandHandler("pham_vi", setrange_command))
    application.add_handler(CommandHandler("bat_dau", startsession_command))
    application.add_handler(CommandHandler("ket_thuc", endsession_command))
    application.add_handler(CommandHandler("toggle_remove", toggle_remove_command))

    # Player management
    application.add_handler(CommandHandler("tham_gia", join_command))
    application.add_handler(CommandHandler("danh_sach", players_command))
    application.add_handler(CommandHandler("lay_ve", layve_command))
    application.add_handler(CommandHandler("tra_ve", out_command))
    application.add_handler(CallbackQueryHandler(lay_ve_callback, pattern="^lay_ve:"))

    # Spin & Status
    application.add_handler(CommandHandler("quay", spin_command))
    application.add_handler(CommandHandler("kinh", check_command))
    application.add_handler(CommandHandler("xoa_kinh", xoakinh_command))
    application.add_handler(CommandHandler("lich_su", history_command))
    application.add_handler(CommandHandler("trang_thai", status_command))
    application.add_handler(CommandHandler("dat_lai", reset_command))
    application.add_handler(CommandHandler("xoa", clear_command))
    application.add_handler(CommandHandler("ket_qua", lastresult_command))
    application.add_handler(CommandHandler("xep_hang", leaderboard_command))
    application.add_handler(CommandHandler("tro_giup", help_command))

    # Glue handlers
    application.add_handler(CallbackQueryHandler(generic_command_callback, pattern="^cmd:"))
    application.add_handler(MessageHandler(filters.REPLY & filters.TEXT & filters.ChatType.PRIVATE, handle_force_reply))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    
    return application

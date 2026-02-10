""" 
Telegram bot handlers và commands 
""" 
import logging
import sys
from pathlib import Path
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

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
    handle_force_reply,
    member_discovery_handler,
    new_member_handler
)

# Import game handlers
from src.bot.handlers.game import (
    newsession_command,
    setrange_command,
    startsession_command,
    endsession_command,
    toggle_remove_command,
    cuoc_command,
    reset_kinh_command
)

# Import player handlers
from src.bot.handlers.player import (
    join_command,
    out_command,
    players_command,
    layve_command,
    lay_ve_callback,
    my_ticket_command
)


# Import spin/status handlers
from src.bot.handlers.spin import (
    spin_command,
    reset_command,
    status_command,
    history_command,
    clear_command,
    lastresult_command,
    check_command,
    xoakinh_command,
    stop_spin_command
)

# Import leaderboard handler
from src.bot.handlers.leaderboard import leaderboard_command, show_user_token_command, reset_token_command, xoa_token_command, bao_danh_callback

# Import wait handler
from src.bot.handlers.wait import wait_command

# Import admin handler
from src.bot.handlers.admin import account_list_command, set_token_command, group_list_command, system_stats_command, broadcast_command, backup_command

# Import inline handler
from src.bot.handlers.inline import inline_query_handler
from telegram.ext import InlineQueryHandler

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
from src.bot.queue_manager import queue_manager
from src.bot.worker import queued_handler
logger = logging.getLogger(__name__)

@queued_handler
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
            ("moi", "Tạo game mới"),
            ("quay", "Quay số"),
            ("dung", "Dừng quay tự động"),
            ("kinh", "Kiểm tra vé (Kinh!)"),
            ("danh_sach", "Người chơi"),
            ("lay_ve", "Lấy vé"),
            ("ve_cua_toi", "Xem vé của tôi"),
            ("trang_thai", "Trạng thái"),
            ("ket_thuc", "Kết thúc game"),
            ("xem_token", "Xem token cá nhân"),
            ("xoa_token", "Xóa token 1 người"),
            ("clear_token", "Xóa sạch Token cả nhóm"),
            ("reset_token", "Reset Token về 0"),
            ("xep_hang", "BXH tổng"),
            ("doi", "Đợi số"),
            ("cuoc", "Đặt tiền cược"),
            ("reset_kinh", "Reset danh sách kinh"),
            ("danh_sach_nhom", "Danh sách nhóm (Admin)"),
            ("he_thong", "Thống kê (Admin)"),
            ("thong_bao", "Thông báo (Admin)"),
            ("back_up", "Sao lưu dữ liệu (Admin)"),
            ("tro_giup", "Trợ giúp")
        ])
        # Bắt đầu worker pool để xử lý hàng đợi
        queue_manager.start()

    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )
    
    # Base commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))

    # Game management
    application.add_handler(CommandHandler("moi", newsession_command))
    application.add_handler(CommandHandler("pham_vi", setrange_command))
    application.add_handler(CommandHandler("bat_dau", startsession_command))
    application.add_handler(CommandHandler("ket_thuc", endsession_command))
    application.add_handler(CommandHandler("toggle_remove", toggle_remove_command))
    application.add_handler(CommandHandler("cuoc", cuoc_command))
    application.add_handler(CommandHandler("reset_kinh", reset_kinh_command))

    # Player management
    application.add_handler(CommandHandler("tham_gia", join_command))
    application.add_handler(CommandHandler("danh_sach", players_command))
    application.add_handler(CommandHandler("lay_ve", layve_command))
    application.add_handler(CommandHandler("ve_cua_toi", my_ticket_command))
    application.add_handler(CommandHandler("tra_ve", out_command))
    application.add_handler(CallbackQueryHandler(lay_ve_callback, pattern="^lay_ve:"))
    application.add_handler(CallbackQueryHandler(bao_danh_callback, pattern="^bao_danh$"))

    # Spin & Status
    application.add_handler(CommandHandler("quay", spin_command))
    application.add_handler(CommandHandler("dung", stop_spin_command))
    application.add_handler(CommandHandler("kinh", check_command))
    application.add_handler(CommandHandler("xoa_kinh", xoakinh_command))
    application.add_handler(CommandHandler("lich_su", history_command))
    application.add_handler(CommandHandler("trang_thai", status_command))
    application.add_handler(CommandHandler("dat_lai", reset_command))
    application.add_handler(CommandHandler("xoa", clear_command))
    application.add_handler(CommandHandler("ket_qua", lastresult_command))
    application.add_handler(CommandHandler("xem_token", show_user_token_command))
    application.add_handler(CommandHandler("xoa_token", xoa_token_command))
    application.add_handler(CommandHandler("clear_token", reset_token_command))
    application.add_handler(CommandHandler("reset_token", reset_token_command))
    application.add_handler(CommandHandler("xep_hang", leaderboard_command))
    application.add_handler(CommandHandler("doi", wait_command))
    application.add_handler(CommandHandler("tro_giup", help_command))
    
    # Admin commands
    application.add_handler(CommandHandler("account_list", account_list_command))
    application.add_handler(CommandHandler("set_token", set_token_command))
    application.add_handler(CommandHandler("danh_sach_nhom", group_list_command))
    application.add_handler(CommandHandler("he_thong", system_stats_command))
    application.add_handler(CommandHandler("thong_bao", broadcast_command))
    application.add_handler(CommandHandler("back_up", backup_command))

    # Inline Query Handler
    application.add_handler(InlineQueryHandler(inline_query_handler))

    # Glue handlers
    application.add_handler(CallbackQueryHandler(generic_command_callback, pattern="^cmd:"))
    application.add_handler(MessageHandler(filters.REPLY & filters.TEXT, handle_force_reply))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    
    # Passive member discovery (capture user info from group chat)
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, member_discovery_handler))
    
    return application

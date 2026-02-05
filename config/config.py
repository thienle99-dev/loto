"""
Configuration cho Telegram bot
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# Bot Settings
MAX_NUMBERS = 90  # Giới hạn số lượng số trong danh sách
DEFAULT_REMOVE_AFTER_SPIN = True  # Mặc định có loại bỏ số sau khi quay

# Messages
WELCOME_MESSAGE = """
🎰 *Chào mừng đến với Loto Bot\\!*

Bot quay số ngẫu nhiên với các tính năng:
• Chọn danh sách số từ x -> y
• Quay wheel và chọn số ngẫu nhiên
• Tùy chọn loại bỏ số sau khi quay
• Reset danh sách về trạng thái ban đầu

📋 *Các lệnh:*
/start - Bắt đầu hoặc xem hướng dẫn
/setrange <x> <y> - Thiết lập khoảng số \\(ví dụ: /setrange 1 100\\)
/spin - Quay wheel
/toggle_remove - Bật/tắt chế độ loại bỏ số
/reset - Reset danh sách về ban đầu
/status - Xem trạng thái hiện tại
/clear - Xóa toàn bộ và bắt đầu lại
/help - Xem hướng dẫn chi tiết
"""

HELP_MESSAGE = """
📖 *Hướng dẫn sử dụng:*

1️⃣ *Thiết lập khoảng số:*
   `/setrange 1 100` - Tạo danh sách từ 1 đến 100

2️⃣ *Quay wheel:*
   `/spin` - Quay và chọn một số ngẫu nhiên

3️⃣ *Quản lý chế độ:*
   `/toggle_remove` - Bật/tắt việc loại bỏ số sau khi quay
   • Bật: Số đã quay sẽ bị loại bỏ (không thể quay lại)
   • Tắt: Số đã quay vẫn có thể xuất hiện lại

4️⃣ *Reset:*
   `/reset` - Khôi phục danh sách số về ban đầu

5️⃣ *Xem trạng thái:*
   `/status` - Xem thông tin chi tiết về session hiện tại

6️⃣ *Xóa toàn bộ:*
   `/clear` - Xóa session và bắt đầu lại từ đầu

💡 *Ví dụ:*
`/setrange 1 50`
`/spin`
`/spin`
`/toggle_remove`
`/spin`
`/reset`
"""

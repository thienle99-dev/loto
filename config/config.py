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
Bot hỗ trợ chơi loto / quay số trong nhóm chat với nhiều tiện ích quản lý phòng chơi.

📖 *Flow cơ bản:*
1️⃣ Host tạo game mới trong chat  
   • `/moi <tên_game>` \\- tạo game với dãy mặc định `1 -> {MAX_NUMBERS}`  
   • Hoặc `/phamvi <x> <y>` \\- tự chọn khoảng số  

2️⃣ Host bắt đầu game  
   • `/batdau` \\- sau khi đã tạo game

3️⃣ Người chơi tham gia và lấy vé  
   • `/thamgia` \\- tham gia game hiện tại  
   • `/danhsach` \\- xem danh sách người chơi  
   • `/out` \\- rời game nếu *chưa* start  
   • Sau khi host quay số, người chơi dùng `/kinh <dãy_số>` để kiểm tra vé  
   • Nếu có *ít nhất 5 số* khớp với các số đã quay (và không có số ngoài dãy) thì được tính là *trúng thưởng*

4️⃣ Host kết thúc game  
   • `/ketthuc` \\- kết thúc game hiện tại  
   • `/ketqua` \\- xem lại kết quả game gần nhất trong chat  
   • `/xephang` hoặc `/leaderboard join` \\- xem bảng xếp hạng

ℹ️ *Lệnh nhanh khác:*  
• `/quay` \\- quay số (chỉ sau khi `/batdau`)  
• `/trangthai` \\- xem trạng thái game hiện tại  
• `/lichsu` \\- lịch sử quay của game  
• `/datlai` \\- reset lại dãy số của game đang chơi  
• `/xoa` \\- xoá session trong chat  
• `/menu` \\- mở bàn phím nhanh các lệnh  
• `/trogiup` \\- xem lại hướng dẫn chi tiết
"""

HELP_MESSAGE = """
📖 *Hướng dẫn chi tiết Loto Bot:*

1️⃣ *Tạo game & bắt đầu chơi (Host)*
   • `/moi <tên_game>` \\- tạo game mới với dãy mặc định `1 -> {MAX_NUMBERS}`  
     Ví dụ: `/moi Loto tối nay`  
   • Hoặc: `/phamvi 1 90` \\- tự chọn khoảng số cho game  
   • `/batdau` \\- host bấm để *bắt đầu* game (sau đó mới được `/quay` và `/kinh`)

2️⃣ *Người chơi tham gia game*
   • `/thamgia` \\- tham gia game hiện tại trong chat  
   • `/danhsach` \\- xem danh sách người đang tham gia  
   • `/out` \\- rời game nếu game *chưa start*  

3️⃣ *Quay số & kiểm tra vé*
   • `/quay` \\- quay số (chỉ khi game đã `/batdau`)  
   • `/lichsu` \\- xem toàn bộ lịch sử quay của game hiện tại  
   • `/trangthai` \\- xem trạng thái game: khoảng số, đã quay bao nhiêu lần, còn bao nhiêu số,...  
   • `/kinh <dãy_số>` \\- kiểm tra vé, ví dụ:
     `/kinh 1 5 10 20 30` hoặc `/kinh 1,5,10,20,30`  
     → Nếu vé có *ít nhất 5 số* đã quay, không có số ngoài dãy, bot sẽ báo *trúng thưởng* kèm các số khớp

4️⃣ *Kết thúc & xem lại kết quả*
   • `/ketthuc` \\- chỉ host \\(người tạo game\\) mới được phép kết thúc game  
   • `/ketqua` \\- xem lại kết quả game gần nhất trong chat: tên game, host, số đã quay, danh sách người trúng  
   • `/xephang` \\- top người trúng thưởng nhiều nhất  
   • `/leaderboard join` \\- top người tham gia nhiều game nhất

5️⃣ *Quản lý & tiện ích khác*
   • `/datlai` \\- reset dãy số của game hiện tại về ban đầu  
   • `/xoa` \\- xoá session trong chat  
   • `/menu` \\- mở bàn phím nhanh các lệnh thường dùng  

💡 *Ví dụ flow đầy đủ:*  
`/moi Loto tối nay`  
`/batdau`  
Mọi người: `/thamgia` → host: `/quay` vài lần → mọi người: `/kinh 1 5 10 20 30`  
Kết thúc: `/ketthuc` → xem lại: `/ketqua` → xem top: `/xephang`
"""

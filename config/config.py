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
   • `/newsession <tên_game>` \\- tạo game với dãy mặc định `1 -> {MAX_NUMBERS}`  
   • Hoặc `/setrange <x> <y>` \\- tự chọn khoảng số  

2️⃣ Host bắt đầu game  
   • `/startsession` \\- sau khi đã tạo game

3️⃣ Người chơi tham gia và lấy vé  
   • `/join` \\- tham gia game hiện tại  
   • `/players` \\- xem danh sách người chơi  
   • `/out` \\- rời game nếu *chưa* start  
   • Sau khi host quay số, người chơi dùng `/check <dãy_số>` để kiểm tra vé  
   • Nếu có *ít nhất 4 số* khớp với các số đã quay (và không có số ngoài dãy) thì được tính là *trúng thưởng*

4️⃣ Host kết thúc game  
   • `/endsession` \\- kết thúc game hiện tại  
   • `/lastresult` \\- xem lại kết quả game gần nhất trong chat  
   • `/leaderboard` hoặc `/leaderboard join` \\- xem bảng xếp hạng

ℹ️ *Lệnh nhanh khác:*  
• `/spin` \\- quay số (chỉ sau khi `/startsession`)  
• `/status` \\- xem trạng thái game hiện tại  
• `/history` \\- lịch sử quay gần đây  
• `/reset` \\- reset lại dãy số của game đang chơi  
• `/clear` \\- xoá session trong chat  
• `/menu` \\- mở bàn phím nhanh các lệnh  
• `/help` \\- xem lại hướng dẫn chi tiết
"""

HELP_MESSAGE = """
📖 *Hướng dẫn chi tiết Loto Bot:*

1️⃣ *Tạo game & bắt đầu chơi (Host)*
   • `/newsession <tên_game>` \\- tạo game mới với dãy mặc định `1 -> {MAX_NUMBERS}`  
     Ví dụ: `/newsession Loto tối nay`  
   • Hoặc: `/setrange 1 90` \\- tự chọn khoảng số cho game  
   • `/startsession` \\- host bấm để *bắt đầu* game (sau đó mới được `/spin` và `/check`)

2️⃣ *Người chơi tham gia game*
   • `/join` \\- tham gia game hiện tại trong chat  
   • `/players` \\- xem danh sách người đang tham gia  
   • `/out` \\- rời game nếu game *chưa start*  

3️⃣ *Quay số & kiểm tra vé*
   • `/spin` \\- quay số (chỉ khi game đã `/startsession`)  
   • `/history` \\- xem lịch sử quay gần đây  
   • `/status` \\- xem trạng thái game: khoảng số, đã quay bao nhiêu lần, còn bao nhiêu số,...  
   • `/check <dãy_số>` \\- kiểm tra vé, ví dụ:
     `/check 1 5 10 20` hoặc `/check 1,5,10,20`  
     → Nếu vé có *ít nhất 4 số* đã quay, không có số ngoài dãy, bot sẽ báo *trúng thưởng* kèm các số khớp

4️⃣ *Kết thúc & xem lại kết quả*
   • `/endsession` \\- chỉ host \\(người tạo game\\) mới được phép kết thúc game  
   • `/lastresult` \\- xem lại kết quả game gần nhất trong chat: tên game, host, số đã quay, danh sách người trúng  
   • `/leaderboard` \\- top người trúng thưởng nhiều nhất  
   • `/leaderboard join` \\- top người tham gia nhiều game nhất

5️⃣ *Quản lý & tiện ích khác*
   • `/reset` \\- reset dãy số của game hiện tại về ban đầu  
   • `/clear` \\- xoá session trong chat  
   • `/menu` \\- mở bàn phím nhanh các lệnh thường dùng  

💡 *Ví dụ flow đầy đủ:*  
`/newsession Loto tối nay`  
`/startsession`  
Mọi người: `/join` → host: `/spin` vài lần → mọi người: `/check 1 5 10 20`  
Kết thúc: `/endsession` → xem lại: `/lastresult` → xem top: `/leaderboard`
"""
